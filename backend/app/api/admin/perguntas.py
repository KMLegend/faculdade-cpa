"""Banco de perguntas (doc 06 §3, política em doc 04 §5.1 e §6.1).

A regra que este módulo existe para proteger: `codigo` é identidade permanente.
Nunca renumerado, nunca reutilizado. Mudança de sentido do enunciado não é
edição — é pergunta nova.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ConflitoEstado, NaoEncontrado
from app.core.security import exigir_admin
from app.db.session import obter_sessao
from app.models import (
    BlocoPergunta, DimensaoSinaes, EixoSinaes, EquivalenciaPergunta, Formulario,
    FormularioPergunta, Pergunta, SEGMENTO_DO_INSTRUMENTO, StatusFormulario,
    Submissao, TipoInstrumento,
)
from app.schemas.perguntas import (
    DimensaoSaida, EixoSaida, ImpactoPergunta, PerguntaEntrada, PerguntaPatch,
    PerguntaSaida,
)

router = APIRouter(dependencies=[Depends(exigir_admin)], tags=["perguntas"])


@router.get("/eixos", response_model=list[EixoSaida])
async def listar_eixos(s: AsyncSession = Depends(obter_sessao)):
    return (await s.scalars(select(EixoSinaes).order_by(EixoSinaes.numero))).all()


@router.get("/dimensoes", response_model=list[DimensaoSaida])
async def listar_dimensoes(s: AsyncSession = Depends(obter_sessao)):
    return (
        await s.scalars(select(DimensaoSinaes).order_by(DimensaoSinaes.numero))
    ).all()


@router.get("/perguntas", response_model=list[PerguntaSaida])
async def listar_perguntas(
    tipo_instrumento: TipoInstrumento | None = None,
    bloco: BlocoPergunta | None = None,
    ativo: bool | None = None,
    s: AsyncSession = Depends(obter_sessao),
):
    q = select(Pergunta).order_by(Pergunta.codigo)
    if tipo_instrumento:
        q = q.where(Pergunta.tipo_instrumento == tipo_instrumento)
    if bloco:
        q = q.where(Pergunta.bloco == bloco)
    if ativo is not None:
        q = q.where(Pergunta.ativo.is_(ativo))
    return (await s.scalars(q)).all()


async def _proximo_codigo(s: AsyncSession) -> int:
    """O próximo livre — NUNCA um código vago de pergunta desativada."""
    maior = await s.scalar(select(func.max(Pergunta.codigo)))
    return (maior or 0) + 1


@router.post("/perguntas", response_model=PerguntaSaida, status_code=201)
async def criar_pergunta(
    dados: PerguntaEntrada, s: AsyncSession = Depends(obter_sessao)
):
    """O `codigo` é atribuído pelo sistema, nunca pelo cliente (doc 04 §5.1)."""
    dimensao = await s.get(DimensaoSinaes, dados.dimensao_id)
    if dimensao is None:
        raise NaoEncontrado("Dimensão não encontrada.")

    equivalencia_id = dados.equivalencia_id
    if equivalencia_id is None:
        grupo = EquivalenciaPergunta(
            rotulo=dados.texto[:240], dimensao_id=dados.dimensao_id
        )
        s.add(grupo)
        await s.flush()
        equivalencia_id = grupo.id
    else:
        grupo = await s.get(EquivalenciaPergunta, equivalencia_id)
        if grupo is None:
            raise NaoEncontrado("Grupo de equivalência não encontrado.")
        if grupo.dimensao_id != dados.dimensao_id:
            raise ConflitoEstado(
                "Membros de um grupo de equivalência precisam compartilhar a dimensão.",
                {
                    "dimensao_do_grupo": grupo.dimensao_id,
                    "dimensao_informada": dados.dimensao_id,
                },
            )

    pergunta = Pergunta(
        **dados.model_dump(exclude={"equivalencia_id"}),
        equivalencia_id=equivalencia_id,
        codigo=await _proximo_codigo(s),
    )
    s.add(pergunta)
    await s.commit()
    await s.refresh(pergunta)
    return pergunta


@router.get("/perguntas/{codigo}/impacto", response_model=ImpactoPergunta)
async def impacto_da_pergunta(codigo: int, s: AsyncSession = Depends(obter_sessao)):
    """Alcance da alteração (doc 04 §6.1) — o admin vê ANTES de confirmar.

    Sem isto, edita às cegas e só descobre o efeito quando o relatório sai errado.
    """
    pergunta = await s.scalar(select(Pergunta).where(Pergunta.codigo == codigo))
    if pergunta is None:
        raise NaoEncontrado(f"Pergunta Q{codigo} não encontrada.")

    base = (
        select(Formulario.id, Formulario.status)
        .join(FormularioPergunta, FormularioPergunta.formulario_id == Formulario.id)
        .where(FormularioPergunta.codigo == codigo)
        .distinct()
    ).subquery()

    formularios = (await s.execute(select(base))).all()
    publicados = sum(1 for f in formularios if f.status == StatusFormulario.PUBLICADO)

    congelados = await s.scalar(
        select(func.count(func.distinct(Submissao.formulario_id)))
        .select_from(Submissao)
        .join(
            FormularioPergunta,
            FormularioPergunta.formulario_id == Submissao.formulario_id,
        )
        .where(FormularioPergunta.codigo == codigo)
    )

    return ImpactoPergunta(
        codigo=codigo,
        formularios=len(formularios),
        publicados=publicados,
        congelados=congelados or 0,
        rascunhos=len(formularios) - publicados,
        proximo_codigo_livre=await _proximo_codigo(s),
    )


@router.patch("/perguntas/{codigo}", response_model=PerguntaSaida)
async def editar_pergunta(
    codigo: int, dados: PerguntaPatch, s: AsyncSession = Depends(obter_sessao)
):
    """Edita uma pergunta existente.

    Alterar o enunciado exige declarar se é correção de redação. Se o sentido
    mudou, o caminho é criar outra pergunta — não editar esta (doc 04 §6.1).
    """
    pergunta = await s.scalar(select(Pergunta).where(Pergunta.codigo == codigo))
    if pergunta is None:
        raise NaoEncontrado(f"Pergunta Q{codigo} não encontrada.")

    campos = dados.model_dump(exclude_unset=True)
    correcao = campos.pop("correcao_de_redacao", None)
    # Apara antes de comparar E antes de gravar: espaço nas pontas não é
    # alteração de enunciado, e não pode vazar para o snapshot do formulário.
    if campos.get("texto") is not None:
        campos["texto"] = campos["texto"].strip()
    texto_novo = campos.get("texto")

    if texto_novo is not None and texto_novo != pergunta.texto.strip():
        if correcao is None:
            raise ConflitoEstado(
                "O enunciado mudou. Informe `correcao_de_redacao` para declarar se as "
                "respostas antigas e as novas podem entrar na mesma média.",
                {"codigo": codigo, "proximo_codigo_livre": await _proximo_codigo(s)},
            )
        if correcao is False:
            raise ConflitoEstado(
                "Mudança de sentido exige pergunta nova: crie com POST /perguntas e "
                "desative esta. Editar somaria duas perguntas diferentes no histórico.",
                {"codigo": codigo, "proximo_codigo_livre": await _proximo_codigo(s)},
            )
        pergunta.versao_texto += 1

    for k, v in campos.items():
        setattr(pergunta, k, v)
    await s.commit()
    await s.refresh(pergunta)
    return pergunta


@router.delete("/perguntas/{codigo}", response_model=PerguntaSaida)
async def desativar_pergunta(codigo: int, s: AsyncSession = Depends(obter_sessao)):
    """Soft delete. O código fica vago PARA SEMPRE — nunca é reaproveitado."""
    pergunta = await s.scalar(select(Pergunta).where(Pergunta.codigo == codigo))
    if pergunta is None:
        raise NaoEncontrado(f"Pergunta Q{codigo} não encontrada.")
    pergunta.ativo = False
    await s.commit()
    await s.refresh(pergunta)
    return pergunta


@router.post("/perguntas/previa")
async def previa_perguntas_turma(
    dados: dict,
    s: AsyncSession = Depends(obter_sessao),
):
    """Monta a estrutura para uma turma sem persistir (doc 06 §3, doc 04 §7)."""
    turma_id = dados.get("turma_id")
    if not turma_id:
        raise ConflitoEstado("Campo turma_id é obrigatório.")

    from app.models import Turma
    from app.services.formularios import (
        LIMITE_ALERTA_PERGUNTAS, SEGUNDOS_POR_PERGUNTA, montar,
    )

    turma = await s.scalar(
        select(Turma).where(Turma.id == turma_id).options(selectinload(Turma.curso))
    )
    if turma is None:
        raise NaoEncontrado(f"Turma {turma_id} não encontrada.")

    dummy_form = Formulario(
        periodo_letivo_id=turma.periodo_letivo_id,
        tipo_instrumento=TipoInstrumento.DISCENTE_TURMA,
        segmento=SEGMENTO_DO_INSTRUMENTO[TipoInstrumento.DISCENTE_TURMA],
        turma_id=turma.id,
        titulo=f"Prévia — {turma.rotulo}",
        status=StatusFormulario.RASCUNHO,
    )
    dummy_form.turma = turma

    itens = await montar(dummy_form, s)
    total_perguntas = len(itens)
    inst_count = sum(1 for it in itens if it.bloco == BlocoPergunta.INSTITUCIONAL)
    ofertas_ids = {it.oferta_id for it in itens if it.oferta_id is not None}
    total_ofertas = len(ofertas_ids)
    por_materia = (total_perguntas - inst_count) // total_ofertas if total_ofertas > 0 else 0

    return {
        "turma_id": turma.id,
        "total_perguntas": total_perguntas,
        "perguntas_institucionais": inst_count,
        "perguntas_por_materia": por_materia,
        "total_ofertas": total_ofertas,
        "tempo_estimado_min": max(1, round((total_perguntas * SEGUNDOS_POR_PERGUNTA) / 60)),
        "acima_do_limite": total_perguntas > LIMITE_ALERTA_PERGUNTAS,
    }

