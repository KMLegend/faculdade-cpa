"""Importação da grade (doc 06 §3).

O fluxo é deliberadamente em duas etapas: `POST /importacoes` só prepara o
staging; é `POST /{id}/aplicar` que grava no domínio, e só com zero pendências.
"""

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import obter_settings
from app.core.errors import ConflitoEstado, NaoEncontrado
from app.core.security import exigir_admin
from app.core.texto import slugificar
from app.db.session import obter_sessao
from app.models import (
    Disciplina, DisciplinaAlias, ImportacaoGrade, ImportacaoLinha, Professor,
    ProfessorAlias, StatusImportacao, StatusLinha,
)
from app.schemas.importacao import (
    DecisaoLinha, DiffSaida, ImportacaoSaida, LinhaSaida,
)
from app.services.importador.commit import aplicar, calcular_diff
from app.services.importador.staging import (
    criar_entidades_novas_em_lote, criar_importacao,
)

router = APIRouter(dependencies=[Depends(exigir_admin)], tags=["importação"])

ASSINATURA_XLSX = b"PK\x03\x04"


@router.post("/importacoes", response_model=ImportacaoSaida, status_code=201)
async def enviar_planilha(
    arquivo: UploadFile = File(...),
    periodo_letivo_id: int = Form(...),
    s: AsyncSession = Depends(obter_sessao),
):
    """Passos 1–5 do pipeline. NADA é gravado no domínio aqui (RN-13)."""
    settings = obter_settings()
    conteudo = await arquivo.read()

    limite = settings.max_upload_mb * 1024 * 1024
    if len(conteudo) > limite:
        raise ConflitoEstado(
            f"Arquivo acima de {settings.max_upload_mb} MB.",
            {"tamanho_bytes": len(conteudo)},
        )
    # Valida extensão E assinatura: .xlsx é um ZIP (doc 08 §2).
    if not (arquivo.filename or "").lower().endswith(".xlsx"):
        raise ConflitoEstado("Envie um arquivo .xlsx.", {"arquivo": arquivo.filename})
    if not conteudo.startswith(ASSINATURA_XLSX):
        raise ConflitoEstado(
            "O arquivo não é um .xlsx válido (assinatura ZIP ausente).", {}
        )

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(conteudo)
        caminho = Path(tmp.name)
    try:
        importacao = await criar_importacao(
            caminho, arquivo.filename or "grade.xlsx", periodo_letivo_id, s
        )
        await s.commit()
        await s.refresh(importacao)
        return importacao
    finally:
        caminho.unlink(missing_ok=True)


@router.get("/importacoes", response_model=list[ImportacaoSaida])
async def listar(
    periodo_letivo_id: int | None = None, s: AsyncSession = Depends(obter_sessao)
):
    q = select(ImportacaoGrade).order_by(ImportacaoGrade.id.desc())
    if periodo_letivo_id:
        q = q.where(ImportacaoGrade.periodo_letivo_id == periodo_letivo_id)
    return (await s.scalars(q)).all()


@router.get("/importacoes/{importacao_id}", response_model=ImportacaoSaida)
async def detalhar(importacao_id: int, s: AsyncSession = Depends(obter_sessao)):
    imp = await s.get(ImportacaoGrade, importacao_id)
    if imp is None:
        raise NaoEncontrado("Importação não encontrada.")
    return imp


@router.get("/importacoes/{importacao_id}/linhas", response_model=list[LinhaSaida])
async def listar_linhas(
    importacao_id: int,
    status: StatusLinha | None = None,
    aba: str | None = None,
    limite: int = Query(500, ge=1, le=2000),
    s: AsyncSession = Depends(obter_sessao),
):
    q = (
        select(ImportacaoLinha)
        .where(ImportacaoLinha.importacao_id == importacao_id)
        .order_by(ImportacaoLinha.id)
        .limit(limite)
    )
    if status:
        q = q.where(ImportacaoLinha.status == status)
    if aba:
        q = q.where(ImportacaoLinha.aba == aba)
    return (await s.scalars(q)).all()


@router.patch(
    "/importacoes/{importacao_id}/linhas/{linha_id}", response_model=LinhaSaida
)
async def decidir_linha(
    importacao_id: int,
    linha_id: int,
    decisao: DecisaoLinha,
    s: AsyncSession = Depends(obter_sessao),
):
    """A decisão do admin — e o alias que a torna definitiva."""
    linha = await s.get(ImportacaoLinha, linha_id)
    if linha is None or linha.importacao_id != importacao_id:
        raise NaoEncontrado("Linha não encontrada nesta importação.")

    if decisao.professor_id:
        prof = await s.get(Professor, decisao.professor_id)
        if prof is None:
            raise NaoEncontrado("Professor não encontrado.")
        linha.professor_id_sugerido = prof.id
        if decisao.criar_alias and linha.professor_proposto:
            await _alias_professor(s, prof, linha.professor_proposto)
    elif decisao.professor_novo:
        linha.professor_proposto = decisao.professor_novo
        linha.professor_id_sugerido = None

    if decisao.disciplina_id:
        disc = await s.get(Disciplina, decisao.disciplina_id)
        if disc is None:
            raise NaoEncontrado("Disciplina não encontrada.")
        linha.disciplina_id_sugerida = disc.id
        if decisao.criar_alias and linha.disciplina_proposta:
            await _alias_disciplina(s, disc, linha.disciplina_proposta)
    elif decisao.disciplina_nova:
        linha.disciplina_proposta = decisao.disciplina_nova
        linha.disciplina_id_sugerida = None

    if decisao.status:
        linha.status = decisao.status
    linha.decisao_admin = {
        **(linha.decisao_admin or {}),
        **decisao.model_dump(exclude_none=True),
    }
    await s.commit()
    await s.refresh(linha)
    return linha


@router.post("/importacoes/{importacao_id}/criar-novas")
async def criar_novas_em_lote(
    importacao_id: int, s: AsyncSession = Depends(obter_sessao)
):
    """Promove as linhas cujo único pendente é entidade nova (doc 03 §4.1)."""
    if await s.get(ImportacaoGrade, importacao_id) is None:
        raise NaoEncontrado("Importação não encontrada.")
    resultado = await criar_entidades_novas_em_lote(importacao_id, s)
    await s.commit()
    return resultado


@router.get("/importacoes/{importacao_id}/diff", response_model=DiffSaida)
async def diff(importacao_id: int, s: AsyncSession = Depends(obter_sessao)):
    """Prévia do commit — reimportar o mesmo arquivo precisa dar `vazio: true`."""
    return (await calcular_diff(importacao_id, s)).como_dict()


@router.post("/importacoes/{importacao_id}/aplicar")
async def aplicar_importacao(
    importacao_id: int, s: AsyncSession = Depends(obter_sessao)
):
    """Grava no domínio. `409` se houver qualquer linha pendente (RN-13)."""
    return await aplicar(importacao_id, s)


@router.delete("/importacoes/{importacao_id}", response_model=ImportacaoSaida)
async def cancelar(importacao_id: int, s: AsyncSession = Depends(obter_sessao)):
    imp = await s.get(ImportacaoGrade, importacao_id)
    if imp is None:
        raise NaoEncontrado("Importação não encontrada.")
    if imp.status == StatusImportacao.APLICADA:
        raise ConflitoEstado("Importação já aplicada não pode ser cancelada.", {})
    imp.status = StatusImportacao.CANCELADA
    await s.commit()
    await s.refresh(imp)
    return imp


async def _alias_professor(s: AsyncSession, prof: Professor, texto: str) -> None:
    slug = slugificar(texto)
    if slug == prof.slug:
        return
    if not await s.scalar(
        select(ProfessorAlias).where(ProfessorAlias.slug_origem == slug)
    ):
        s.add(ProfessorAlias(professor_id=prof.id, texto_origem=texto, slug_origem=slug))


async def _alias_disciplina(s: AsyncSession, disc: Disciplina, texto: str) -> None:
    slug = slugificar(texto)
    if slug == disc.slug:
        return
    if not await s.scalar(
        select(DisciplinaAlias).where(DisciplinaAlias.slug_origem == slug)
    ):
        s.add(
            DisciplinaAlias(disciplina_id=disc.id, texto_origem=texto, slug_origem=slug)
        )
