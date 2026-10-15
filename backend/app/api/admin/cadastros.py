"""CRUD dos cadastros acadêmicos (doc 06 §3).

`DELETE` é sempre soft (`ativo = false`) — nunca físico em entidade que pode
estar referenciada por um formulário publicado (doc 00, convenção 4).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflitoEstado, NaoEncontrado
from app.core.security import exigir_admin
from app.core.texto import slugificar
from app.db.session import obter_sessao
from app.models import (
    Curso, Disciplina, Oferta, OfertaTurma, PeriodoLetivo, Professor, Turma,
)
from app.schemas.academico import (
    CursoSaida, DisciplinaEntrada, DisciplinaPatch, DisciplinaSaida, OfertaPatch,
    OfertaSaida, PeriodoLetivoSaida, ProfessorEntrada, ProfessorPatch,
    ProfessorSaida, TurmaSaida,
)

router = APIRouter(dependencies=[Depends(exigir_admin)], tags=["cadastros"])


# ─── períodos letivos ────────────────────────────────────────────────────────
@router.get("/periodos-letivos", response_model=list[PeriodoLetivoSaida])
async def listar_periodos(s: AsyncSession = Depends(obter_sessao)):
    return (
        await s.scalars(select(PeriodoLetivo).order_by(PeriodoLetivo.codigo.desc()))
    ).all()


# ─── cursos ──────────────────────────────────────────────────────────────────
@router.get("/cursos", response_model=list[CursoSaida])
async def listar_cursos(s: AsyncSession = Depends(obter_sessao)):
    return (await s.scalars(select(Curso).order_by(Curso.nome))).all()


# ─── professores ─────────────────────────────────────────────────────────────
@router.get("/professores", response_model=list[ProfessorSaida])
async def listar_professores(
    ativo: bool | None = None, s: AsyncSession = Depends(obter_sessao)
):
    q = select(Professor).order_by(Professor.nome_exibicao)
    if ativo is not None:
        q = q.where(Professor.ativo.is_(ativo))
    return (await s.scalars(q)).all()


@router.post("/professores", response_model=ProfessorSaida, status_code=201)
async def criar_professor(
    dados: ProfessorEntrada, s: AsyncSession = Depends(obter_sessao)
):
    slug = slugificar(dados.nome_exibicao)
    if await s.scalar(select(Professor).where(Professor.slug == slug)):
        raise ConflitoEstado(
            f"Já existe professor com o nome '{dados.nome_exibicao}'.",
            {"slug": slug},
        )
    prof = Professor(**dados.model_dump(), slug=slug)
    s.add(prof)
    await s.commit()
    await s.refresh(prof)
    return prof


@router.patch("/professores/{professor_id}", response_model=ProfessorSaida)
async def editar_professor(
    professor_id: int, dados: ProfessorPatch, s: AsyncSession = Depends(obter_sessao)
):
    prof = await s.get(Professor, professor_id)
    if prof is None:
        raise NaoEncontrado("Professor não encontrado.")
    campos = dados.model_dump(exclude_unset=True)
    if "nome_exibicao" in campos:
        campos["slug"] = slugificar(campos["nome_exibicao"])
    for k, v in campos.items():
        setattr(prof, k, v)
    await s.commit()
    await s.refresh(prof)
    return prof


@router.delete("/professores/{professor_id}", response_model=ProfessorSaida)
async def desativar_professor(
    professor_id: int, s: AsyncSession = Depends(obter_sessao)
):
    """Soft delete. Recusa se o professor tem oferta ativa no período."""
    prof = await s.get(Professor, professor_id)
    if prof is None:
        raise NaoEncontrado("Professor não encontrado.")
    em_uso = await s.scalar(
        select(Oferta).where(Oferta.professor_id == professor_id, Oferta.ativo.is_(True))
    )
    if em_uso:
        raise ConflitoEstado(
            "Professor tem ofertas ativas. Desative as ofertas primeiro.",
            {"oferta_id": em_uso.id},
        )
    prof.ativo = False
    await s.commit()
    await s.refresh(prof)
    return prof


# ─── disciplinas ─────────────────────────────────────────────────────────────
@router.get("/disciplinas", response_model=list[DisciplinaSaida])
async def listar_disciplinas(
    ativo: bool | None = None, s: AsyncSession = Depends(obter_sessao)
):
    q = select(Disciplina).order_by(Disciplina.nome)
    if ativo is not None:
        q = q.where(Disciplina.ativo.is_(ativo))
    return (await s.scalars(q)).all()


@router.post("/disciplinas", response_model=DisciplinaSaida, status_code=201)
async def criar_disciplina(
    dados: DisciplinaEntrada, s: AsyncSession = Depends(obter_sessao)
):
    slug = slugificar(dados.nome)
    if await s.scalar(select(Disciplina).where(Disciplina.slug == slug)):
        raise ConflitoEstado(f"Já existe disciplina '{dados.nome}'.", {"slug": slug})
    disc = Disciplina(**dados.model_dump(), slug=slug)
    s.add(disc)
    await s.commit()
    await s.refresh(disc)
    return disc


@router.patch("/disciplinas/{disciplina_id}", response_model=DisciplinaSaida)
async def editar_disciplina(
    disciplina_id: int, dados: DisciplinaPatch, s: AsyncSession = Depends(obter_sessao)
):
    disc = await s.get(Disciplina, disciplina_id)
    if disc is None:
        raise NaoEncontrado("Disciplina não encontrada.")
    campos = dados.model_dump(exclude_unset=True)
    if "nome" in campos:
        campos["slug"] = slugificar(campos["nome"])
    for k, v in campos.items():
        setattr(disc, k, v)
    await s.commit()
    await s.refresh(disc)
    return disc


# ─── turmas ──────────────────────────────────────────────────────────────────
@router.get("/turmas", response_model=list[TurmaSaida])
async def listar_turmas(
    periodo_letivo_id: int | None = None, s: AsyncSession = Depends(obter_sessao)
):
    q = select(Turma).order_by(Turma.curso_id, Turma.turno, Turma.periodo_numero)
    if periodo_letivo_id:
        q = q.where(Turma.periodo_letivo_id == periodo_letivo_id)
    return (await s.scalars(q)).all()


# ─── ofertas ─────────────────────────────────────────────────────────────────
@router.get("/ofertas", response_model=list[OfertaSaida])
async def listar_ofertas(
    periodo_letivo_id: int | None = None,
    avaliavel: bool | None = None,
    s: AsyncSession = Depends(obter_sessao),
):
    q = select(Oferta).order_by(Oferta.id)
    if periodo_letivo_id:
        q = q.where(Oferta.periodo_letivo_id == periodo_letivo_id)
    if avaliavel is not None:
        q = q.where(Oferta.avaliavel.is_(avaliavel))
    return (await s.scalars(q)).all()


@router.patch("/ofertas/{oferta_id}", response_model=OfertaSaida)
async def editar_oferta(
    oferta_id: int, dados: OfertaPatch, s: AsyncSession = Depends(obter_sessao)
):
    """RN-15 — alternar `avaliavel` tira ou devolve a oferta ao formulário."""
    oferta = await s.get(Oferta, oferta_id)
    if oferta is None:
        raise NaoEncontrado("Oferta não encontrada.")
    for k, v in dados.model_dump(exclude_unset=True).items():
        setattr(oferta, k, v)
    await s.commit()
    await s.refresh(oferta)
    return oferta


@router.get("/ofertas/{oferta_id}/turmas", response_model=list[TurmaSaida])
async def turmas_da_oferta(oferta_id: int, s: AsyncSession = Depends(obter_sessao)):
    """RN-07 — uma oferta atende 0..N turmas."""
    if await s.get(Oferta, oferta_id) is None:
        raise NaoEncontrado("Oferta não encontrada.")
    return (
        await s.scalars(
            select(Turma)
            .join(OfertaTurma, OfertaTurma.turma_id == Turma.id)
            .where(OfertaTurma.oferta_id == oferta_id)
        )
    ).all()


@router.put("/ofertas/{oferta_id}/turmas", response_model=list[TurmaSaida])
async def definir_turmas_da_oferta(
    oferta_id: int,
    turma_ids: list[int] = Query(default=[]),
    s: AsyncSession = Depends(obter_sessao),
):
    oferta = await s.get(Oferta, oferta_id)
    if oferta is None:
        raise NaoEncontrado("Oferta não encontrada.")
    atuais = (
        await s.scalars(select(OfertaTurma).where(OfertaTurma.oferta_id == oferta_id))
    ).all()
    for vinculo in atuais:
        await s.delete(vinculo)
    await s.flush()
    for turma_id in dict.fromkeys(turma_ids):
        if await s.get(Turma, turma_id) is None:
            raise NaoEncontrado(f"Turma {turma_id} não encontrada.")
        s.add(OfertaTurma(oferta_id=oferta_id, turma_id=turma_id))
    await s.commit()
    return await turmas_da_oferta(oferta_id, s)
