"""Rotas administrativas de formulários (doc 06 §3, doc 05)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ConflitoEstado, NaoEncontrado
from app.core.security import exigir_admin
from app.db.session import obter_sessao
from app.models import (
    DimensaoSinaes, EstadoSync, Formulario, FormularioPergunta, Oferta,
    OfertaTurma, PeriodoLetivo, StatusFormulario, Submissao, TipoInstrumento,
    Turma,
)
from app.schemas.formularios import (
    BlocoInstitucionalPrevia, BlocoMateriaPrevia, DiffPrevia,
    FormularioCabecalhoPrevia, FormularioItemSaida, GerarLoteEntrada,
    PerguntaPrevia, PreviaFormularioSaida, PublicarLoteEntrada,
    PublicarLoteSaida, ResumoGeracaoSaida, TurmaPrevia,
)
from app.services.formularios import (
    LIMITE_ALERTA_PERGUNTAS, SEGUNDOS_POR_PERGUNTA, encerrar_formulario,
    gerar_lote, publicar_formulario, publicar_lote,
)
from app.services.pdf_service import (
    gerar_conferencia_turma_pdf, gerar_folha_pdf, gerar_folhas_lote_pdf,
)

router = APIRouter(dependencies=[Depends(exigir_admin)], tags=["formulários"])


def _montar_saida_formulario(f: Formulario) -> FormularioItemSaida:
    """Calcula os totais e flags para o item da listagem."""
    total_perguntas = len(f.itens)
    tempo_min = max(1, round((total_perguntas * SEGUNDOS_POR_PERGUNTA) / 60))

    ofertas_ids = {
        item.oferta_id for item in f.itens if item.oferta_id is not None
    }
    total_ofertas = len(ofertas_ids)

    turma_rotulo = f.turma.rotulo if f.turma else None
    modulo = f.turma.modulo if f.turma else None

    # Contagem de submissões
    total_submissoes = len(f.submissoes) if hasattr(f, "submissoes") and f.submissoes else 0

    return FormularioItemSaida(
        id=f.id,
        uuid=f.uuid,
        periodo_letivo_id=f.periodo_letivo_id,
        tipo_instrumento=f.tipo_instrumento,
        segmento=f.segmento,
        titulo=f.titulo,
        turma_id=f.turma_id,
        turma=turma_rotulo,
        modulo=modulo,
        status=f.status,
        abre_em=f.abre_em,
        fecha_em=f.fecha_em,
        google_form_id=f.google_form_id,
        google_responder_uri=f.google_responder_uri,
        estado_sync=f.estado_sync,
        total_ofertas=total_ofertas,
        total_perguntas=total_perguntas,
        tempo_estimado_min=tempo_min,
        acima_do_limite=total_perguntas > LIMITE_ALERTA_PERGUNTAS,
        limite_perguntas=LIMITE_ALERTA_PERGUNTAS,
        submissoes=total_submissoes,
        anonimato_ok=True,
    )


@router.post("/formularios/gerar-lote", response_model=ResumoGeracaoSaida)
async def api_gerar_lote(
    dados: GerarLoteEntrada,
    s: AsyncSession = Depends(obter_sessao),
):
    """Gera em lote os formulários do período (doc 05 §1)."""
    resumo = await gerar_lote(dados.periodo_letivo_id, dados.janelas, s)
    return ResumoGeracaoSaida(**resumo)


@router.post("/formularios/publicar-lote", response_model=PublicarLoteSaida)
async def api_publicar_lote(
    dados: PublicarLoteEntrada,
    s: AsyncSession = Depends(obter_sessao),
):
    """Publica em lote formulários em RASCUNHO (doc 05 §2)."""
    janela = (
        (dados.abre_em, dados.fecha_em) if dados.abre_em and dados.fecha_em else None
    )
    res = await publicar_lote(
        dados.periodo_letivo_id, dados.tipo_instrumento, s, janela=janela
    )
    return PublicarLoteSaida(**res)


@router.get("/formularios", response_model=list[FormularioItemSaida])
async def listar_formularios(
    periodo_letivo_id: int | None = None,
    tipo_instrumento: TipoInstrumento | None = None,
    status: StatusFormulario | None = None,
    s: AsyncSession = Depends(obter_sessao),
):
    """Lista formulários com contadores e status de sincronização (doc 06 §3)."""
    q = (
        select(Formulario)
        .options(
            selectinload(Formulario.itens),
            selectinload(Formulario.turma).selectinload(Turma.curso),
            selectinload(Formulario.submissoes),
        )
        .order_by(Formulario.tipo_instrumento, Formulario.id)
    )

    if periodo_letivo_id is not None:
        q = q.where(Formulario.periodo_letivo_id == periodo_letivo_id)
    if tipo_instrumento is not None:
        q = q.where(Formulario.tipo_instrumento == tipo_instrumento)
    if status is not None:
        q = q.where(Formulario.status == status)

    formularios = (await s.scalars(q)).all()
    return [_montar_saida_formulario(f) for f in formularios]


@router.get("/formularios/{id}", response_model=FormularioItemSaida)
async def obter_formulario(id: int, s: AsyncSession = Depends(obter_sessao)):
    """Obtém detalhes de um formulário."""
    f = await s.scalar(
        select(Formulario)
        .where(Formulario.id == id)
        .options(
            selectinload(Formulario.itens),
            selectinload(Formulario.turma).selectinload(Turma.curso),
            selectinload(Formulario.submissoes),
        )
    )
    if f is None:
        raise NaoEncontrado(f"Formulário {id} não encontrado.")
    return _montar_saida_formulario(f)


@router.get("/formularios/{id}/previa", response_model=PreviaFormularioSaida)
async def previa_formulario(id: int, s: AsyncSession = Depends(obter_sessao)):
    """Pré-visualização da estrutura exata a ser sincronizada com o Google Forms (doc 07 §3.6)."""
    f = await s.scalar(
        select(Formulario)
        .where(Formulario.id == id)
        .options(
            selectinload(Formulario.itens).selectinload(FormularioPergunta.dimensao),
            selectinload(Formulario.itens).selectinload(FormularioPergunta.oferta).selectinload(Oferta.disciplina),
            selectinload(Formulario.itens).selectinload(FormularioPergunta.oferta).selectinload(Oferta.professor),
            selectinload(Formulario.turma).selectinload(Turma.curso),
        )
    )
    if f is None:
        raise NaoEncontrado(f"Formulário {id} não encontrado.")

    total_perguntas = len(f.itens)
    tempo_min = max(1, round((total_perguntas * SEGUNDOS_POR_PERGUNTA) / 60))

    # Dimensões e Blocos Institucionais
    todas_dimensoes = (
        await s.scalars(select(DimensaoSinaes).order_by(DimensaoSinaes.numero))
    ).all()
    dim_map = {d.id: d for d in todas_dimensoes}

    itens_inst = [it for it in f.itens if it.oferta_id is None]
    por_dim: dict[int, list[PerguntaPrevia]] = {}
    for it in itens_inst:
        dim_num = dim_map[it.dimensao_id].numero
        por_dim.setdefault(dim_num, []).append(
            PerguntaPrevia(
                codigo=it.codigo,
                texto=it.texto_snapshot,
                bloco=it.bloco,
                tipo=it.tipo_snapshot,
            )
        )

    blocos_inst = [
        BlocoInstitucionalPrevia(
            dimensao=d.numero,
            nome=d.nome,
            perguntas=por_dim[d.numero],
        )
        for d in todas_dimensoes
        if d.numero in por_dim
    ]

    # Blocos por Matéria
    itens_materia = [it for it in f.itens if it.oferta_id is not None]
    ofertas_map: dict[int, dict] = {}
    for it in itens_materia:
        oid = it.oferta_id
        if oid not in ofertas_map:
            ofertas_map[oid] = {
                "oferta_id": oid,
                "disciplina": it.oferta.disciplina.nome if it.oferta and it.oferta.disciplina else "",
                "professor": it.oferta.professor.nome_exibicao if it.oferta and it.oferta.professor else "",
                "perguntas": [],
            }
        ofertas_map[oid]["perguntas"].append(
            PerguntaPrevia(
                codigo=it.codigo,
                texto=it.texto_snapshot,
                bloco=it.bloco,
                tipo=it.tipo_snapshot,
            )
        )

    blocos_mat = [
        BlocoMateriaPrevia(
            oferta_id=v["oferta_id"],
            disciplina=v["disciplina"],
            professor=v["professor"],
            perguntas=v["perguntas"],
        )
        for v in ofertas_map.values()
    ]

    total_paginas = 1 + len(blocos_inst) + len(blocos_mat)
    qtd_por_materia = len(blocos_mat[0].perguntas) if blocos_mat else 0

    turma_previa = None
    if f.turma:
        turma_previa = TurmaPrevia(
            id=f.turma.id,
            rotulo=f.turma.rotulo,
            modulo=f.turma.modulo,
        )

    diff = None
    if f.estado_sync != EstadoSync.NAO_CRIADO:
        if f.tipo_instrumento == TipoInstrumento.DISCENTE_TURMA:
            diff = DiffPrevia(
                unidade="matérias",
                incluidas=0,
                alteradas=0,
                removidas=0,
                inalteradas=len(blocos_mat),
            )
        else:
            diff = DiffPrevia(
                unidade="perguntas",
                incluidas=0,
                alteradas=0,
                removidas=0,
                inalteradas=total_perguntas,
            )

    return PreviaFormularioSaida(
        formulario=FormularioCabecalhoPrevia(
            id=f.id,
            titulo=f.titulo,
            tipo_instrumento=f.tipo_instrumento,
            segmento=f.segmento,
            estado_sync=f.estado_sync,
            acima_do_limite=total_perguntas > LIMITE_ALERTA_PERGUNTAS,
            limite_perguntas=LIMITE_ALERTA_PERGUNTAS,
        ),
        turma=turma_previa,
        perguntas_institucionais=len(itens_inst),
        perguntas_por_materia=qtd_por_materia,
        total_ofertas=len(blocos_mat),
        total_perguntas=total_perguntas,
        total_paginas=total_paginas,
        tempo_estimado_min=tempo_min,
        blocos_institucionais=blocos_inst,
        blocos_materia=blocos_mat,
        diff=diff,
    )


@router.post("/formularios/{id}/publicar", response_model=FormularioItemSaida)
async def api_publicar_formulario(id: int, s: AsyncSession = Depends(obter_sessao)):
    """Publica um formulário (RASCUNHO -> PUBLICADO)."""
    f = await publicar_formulario(id, s)
    return await obter_formulario(f.id, s)


@router.post("/formularios/{id}/encerrar", response_model=FormularioItemSaida)
async def api_encerrar_formulario(id: int, s: AsyncSession = Depends(obter_sessao)):
    """Encerra um formulário (PUBLICADO -> ENCERRADO)."""
    f = await encerrar_formulario(id, s)
    return await obter_formulario(f.id, s)


@router.delete("/formularios/{id}", response_model=dict)
async def excluir_formulario(id: int, s: AsyncSession = Depends(obter_sessao)):
    """Exclui formulário (permitido apenas em RASCUNHO)."""
    f = await s.get(Formulario, id)
    if f is None:
        raise NaoEncontrado(f"Formulário {id} não encontrado.")

    if f.status != StatusFormulario.RASCUNHO:
        raise ConflitoEstado("Apenas formulários em rascunho podem ser excluídos.")

    await s.delete(f)
    await s.commit()
    return {"status": "ok", "mensagem": f"Formulário {id} excluído com sucesso."}


@router.get("/formularios/{id}/folha.pdf")
async def obter_folha_pdf(id: int, s: AsyncSession = Depends(obter_sessao)):
    """Gera o PDF da folha de aplicação A4 da turma ou cartaz de segmento (doc 05 §4)."""
    f = await s.scalar(
        select(Formulario)
        .where(Formulario.id == id)
        .options(
            selectinload(Formulario.itens),
            selectinload(Formulario.turma).selectinload(Turma.curso),
            selectinload(Formulario.periodo_letivo),
        )
    )
    if f is None:
        raise NaoEncontrado(f"Formulário {id} não encontrado.")

    pdf_bytes = gerar_folha_pdf(f)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="folha_formulario_{id}.pdf"'},
    )


@router.get("/periodos/{id}/folhas.pdf")
async def obter_folhas_periodo_pdf(
    id: int,
    tipo_instrumento: TipoInstrumento | None = None,
    s: AsyncSession = Depends(obter_sessao),
):
    """Gera um PDF único com todas as folhas do período/instrumento concatenadas."""
    q = (
        select(Formulario)
        .where(Formulario.periodo_letivo_id == id)
        .options(
            selectinload(Formulario.itens),
            selectinload(Formulario.turma).selectinload(Turma.curso),
            selectinload(Formulario.periodo_letivo),
        )
        .order_by(Formulario.id)
    )
    if tipo_instrumento:
        q = q.where(Formulario.tipo_instrumento == tipo_instrumento)

    formularios = (await s.scalars(q)).all()
    if not formularios:
        raise NaoEncontrado("Nenhum formulário encontrado para o período informado.")

    pdf_bytes = gerar_folhas_lote_pdf(formularios)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="folhas_periodo_{id}.pdf"'},
    )


@router.get("/turmas/{id}/conferencia.pdf")
async def obter_conferencia_turma_pdf(id: int, s: AsyncSession = Depends(obter_sessao)):
    """Gera a lista de conferência da turma (A4, doc 05 §4.2)."""
    turma = await s.scalar(
        select(Turma)
        .where(Turma.id == id)
        .options(
            selectinload(Turma.curso),
            selectinload(Turma.ofertas_turma)
            .selectinload(OfertaTurma.oferta)
            .selectinload(Oferta.disciplina),
            selectinload(Turma.ofertas_turma)
            .selectinload(OfertaTurma.oferta)
            .selectinload(Oferta.professor),
        )
    )
    if turma is None:
        raise NaoEncontrado(f"Turma {id} não encontrada.")

    pdf_bytes = gerar_conferencia_turma_pdf(turma)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="conferencia_turma_{id}.pdf"'},
    )
