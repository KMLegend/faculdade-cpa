"""Aplicação da importação no domínio (doc 03 §5).

Transação única, na ordem do documento. Só roda com zero linhas pendentes
(RN-13) e é idempotente por período letivo (RN-12): reimportar o mesmo arquivo
produz diff vazio.

⚠️ Formulários já publicados nunca são alterados aqui. Se uma oferta avaliada
for desativada, o formulário mantém seu snapshot e o relatório segue válido.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import delete, select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflitoEstado, NaoEncontrado
from app.core.texto import slugificar
from app.models import (
    Alocacao, Curso, Disciplina, DisciplinaAlias, ImportacaoGrade, ImportacaoLinha,
    Modalidade, Oferta, OfertaTurma, Professor, ProfessorAlias, StatusImportacao,
    StatusLinha, Turma, Turno,
)

DIAS = {
    "segunda": 1, "terca": 2, "terça": 2, "quarta": 3,
    "quinta": 4, "sexta": 5, "sabado": 6, "sábado": 6,
}


async def _indices(s: AsyncSession) -> tuple[dict, dict, dict, dict]:
    """Catálogos por slug + os aliases já conciliados.

    O diff e o commit precisam resolver  → Washington como o
    staging faz; consultar só o slug faria a reimportação criar tudo de novo.
    """
    profs = {p.slug: p for p in (await s.scalars(select(Professor))).all()}
    discs = {d.slug: d for d in (await s.scalars(select(Disciplina))).all()}
    alias_p = {
        a.slug_origem: a.professor_id
        for a in (await s.scalars(select(ProfessorAlias))).all()
    }
    alias_d = {
        a.slug_origem: a.disciplina_id
        for a in (await s.scalars(select(DisciplinaAlias))).all()
    }
    return profs, discs, alias_p, alias_d


def _resolver(slug: str, catalogo: dict, aliases: dict[str, int]):
    """Entidade correspondente ao slug, via catálogo ou alias."""
    if slug in catalogo:
        return catalogo[slug]
    id_ = aliases.get(slug)
    if id_ is None:
        return None
    return next((e for e in catalogo.values() if e.id == id_), None)


def _dia_para_numero(texto: str | None) -> int | None:
    if not texto:
        return None
    alvo = texto.lower().strip()
    for nome, numero in DIAS.items():
        if alvo.startswith(nome):
            return numero
    return None


@dataclass
class Diff:
    """O que o commit faria — mostrado ao admin ANTES de aplicar (RN-12)."""

    turmas_novas: list[str] = field(default_factory=list)
    turmas_existentes: int = 0
    ofertas_novas: list[str] = field(default_factory=list)
    ofertas_existentes: int = 0
    ofertas_desativadas: list[str] = field(default_factory=list)
    professores_novos: list[str] = field(default_factory=list)
    disciplinas_novas: list[str] = field(default_factory=list)
    alocacoes: int = 0

    @property
    def vazio(self) -> bool:
        """Reimportar o mesmo arquivo precisa cair aqui."""
        return not (
            self.turmas_novas
            or self.ofertas_novas
            or self.ofertas_desativadas
            or self.professores_novos
            or self.disciplinas_novas
        )

    def como_dict(self) -> dict:
        return {
            "turmas_novas": self.turmas_novas,
            "turmas_existentes": self.turmas_existentes,
            "ofertas_novas": self.ofertas_novas,
            "ofertas_existentes": self.ofertas_existentes,
            "ofertas_desativadas": self.ofertas_desativadas,
            "professores_novos": self.professores_novos,
            "disciplinas_novas": self.disciplinas_novas,
            "alocacoes": self.alocacoes,
            "vazio": self.vazio,
        }


async def _carregar_pendencias(importacao_id: int, s: AsyncSession) -> list[str]:
    linhas = (
        await s.scalars(
            select(ImportacaoLinha).where(
                ImportacaoLinha.importacao_id == importacao_id,
                ImportacaoLinha.status.in_([StatusLinha.REVISAR, StatusLinha.ERRO]),
            )
        )
    ).all()
    return [f"{l.aba}!{l.celula}: {', '.join(l.motivos or [])}" for l in linhas]


async def calcular_diff(importacao_id: int, s: AsyncSession) -> Diff:
    """Simula o commit sem gravar nada."""
    importacao = await s.get(ImportacaoGrade, importacao_id)
    if importacao is None:
        raise NaoEncontrado(f"Importação {importacao_id} não encontrada.")

    linhas = (
        await s.scalars(
            select(ImportacaoLinha).where(
                ImportacaoLinha.importacao_id == importacao_id,
                ImportacaoLinha.status == StatusLinha.OK,
            )
        )
    ).all()

    periodo_id = importacao.periodo_letivo_id
    diff = Diff(alocacoes=len(linhas))

    cursos = {c.slug: c for c in (await s.scalars(select(Curso))).all()}
    profs, discs, alias_p, alias_d = await _indices(s)
    turmas = {
        (t.curso_id, t.turno.value, t.periodo_numero): t
        for t in (
            await s.scalars(select(Turma).where(Turma.periodo_letivo_id == periodo_id))
        ).all()
    }
    ofertas = {
        (o.disciplina_id, o.professor_id): o
        for o in (
            await s.scalars(
                select(Oferta)
                .where(Oferta.periodo_letivo_id == periodo_id)
                .options(selectinload(Oferta.ofertas_turma))
            )
        ).all()
    }

    vistas_turma: set[tuple] = set()
    vistas_oferta: set[tuple] = set()

    for linha in linhas:
        proposta = linha.turma_proposta or {}
        slug_prof = slugificar(linha.professor_proposto or "")
        slug_disc = slugificar(linha.disciplina_proposta or "")
        if not slug_prof or not slug_disc:
            continue

        prof = _resolver(slug_prof, profs, alias_p)
        disc = _resolver(slug_disc, discs, alias_d)
        if prof is None and linha.professor_proposto not in diff.professores_novos:
            diff.professores_novos.append(linha.professor_proposto)
        if disc is None and linha.disciplina_proposta not in diff.disciplinas_novas:
            diff.disciplinas_novas.append(linha.disciplina_proposta)

        if proposta.get("e_turma"):
            for curso_slug in proposta.get("cursos", []):
                curso = cursos.get(curso_slug)
                if curso is None:
                    continue
                chave = (curso.id, proposta["turno"], proposta["periodo_numero"])
                if chave in vistas_turma:
                    continue
                vistas_turma.add(chave)
                if chave in turmas:
                    diff.turmas_existentes += 1
                else:
                    diff.turmas_novas.append(
                        f"{curso.nome} · {proposta['turno'].title()} · "
                        f"{proposta['periodo_numero']}º período"
                    )

        # / já vêm resolvidos via alias logo acima — não
        # reconsultar pelo slug cru, senão  vira oferta nova a
        # cada reimportação e a RN-12 nunca fecha.
        # A chave de dedupe cai no slug quando a entidade ainda não existe.
        chave_of = (
            disc.id if disc else f"novo:{slug_disc}",
            prof.id if prof else f"novo:{slug_prof}",
        )
        if chave_of in vistas_oferta:
            continue
        vistas_oferta.add(chave_of)

        if prof and disc and (disc.id, prof.id) in ofertas:
            diff.ofertas_existentes += 1
        else:
            diff.ofertas_novas.append(
                f"{disc.nome if disc else linha.disciplina_proposta} · "
                f"{prof.nome_exibicao if prof else linha.professor_proposto}"
            )

    # Ofertas que existem no banco e não aparecem no arquivo
    # (RN-09: só desativa se tivesse turmas antes — ofertas puras de
    # "Estágio I ou II" ou "TCC 1 ou 2" sem oferta_turma são sempre opcionais)
    for (disc_id, prof_id), oferta in ofertas.items():
        if ((disc_id, prof_id) not in vistas_oferta and oferta.ativo
                and len(oferta.ofertas_turma) > 0):
            diff.ofertas_desativadas.append(f"oferta #{oferta.id}")

    return diff


async def aplicar(importacao_id: int, s: AsyncSession) -> dict:
    """Passo 7 do pipeline: grava no domínio, em transação única."""
    importacao = await s.get(ImportacaoGrade, importacao_id)
    if importacao is None:
        raise NaoEncontrado(f"Importação {importacao_id} não encontrada.")
    if importacao.status == StatusImportacao.APLICADA:
        raise ConflitoEstado(
            "Esta importação já foi aplicada.", {"importacao_id": importacao_id}
        )

    pendencias = await _carregar_pendencias(importacao_id, s)
    if pendencias:
        raise ConflitoEstado(
            f"{len(pendencias)} linha(s) ainda em revisão ou com erro. "
            "Nada é gravado enquanto houver pendência (RN-13).",
            {"pendencias": pendencias[:20], "total": len(pendencias)},
        )

    linhas = (
        await s.scalars(
            select(ImportacaoLinha).where(
                ImportacaoLinha.importacao_id == importacao_id,
                ImportacaoLinha.status == StatusLinha.OK,
            )
        )
    ).all()
    periodo_id = importacao.periodo_letivo_id

    # 1) cursos — nunca cria CICLO_BASICO (RN-03)
    cursos = {c.slug: c for c in (await s.scalars(select(Curso))).all()}

    # 2/3) professores e disciplinas — resolvidos via catálogo OU alias
    profs, discs, alias_p, alias_d = await _indices(s)
    criados = {"professores": 0, "disciplinas": 0, "turmas": 0, "ofertas": 0}

    for linha in linhas:
        nome_p, nome_d = linha.professor_proposto, linha.disciplina_proposta
        if not nome_p or not nome_d:
            continue

        if linha.professor_id_sugerido:
            prof = await s.get(Professor, linha.professor_id_sugerido)
        else:
            slug = slugificar(nome_p)
            prof = _resolver(slug, profs, alias_p)
            if prof is None:
                prof = Professor(nome_exibicao=nome_p, slug=slug)
                s.add(prof)
                await s.flush()
                profs[slug] = prof
                criados["professores"] += 1
        # A decisão da conciliação vira alias: na próxima importação casa na etapa 1.
        await _garantir_alias_professor(s, prof, nome_p)

        if linha.disciplina_id_sugerida:
            disc = await s.get(Disciplina, linha.disciplina_id_sugerida)
        else:
            slug = slugificar(nome_d)
            disc = _resolver(slug, discs, alias_d)
            if disc is None:
                disc = Disciplina(nome=nome_d, slug=slug)
                s.add(disc)
                await s.flush()
                discs[slug] = disc
                criados["disciplinas"] += 1
        await _garantir_alias_disciplina(s, disc, nome_d)

        linha.decisao_admin = {
            **(linha.decisao_admin or {}),
            "professor_id": prof.id,
            "disciplina_id": disc.id,
        }

    await s.flush()

    # 4) turmas — chave (periodo, curso, turno, periodo_numero) — RN-04
    turmas = {
        (t.curso_id, t.turno.value, t.periodo_numero): t
        for t in (
            await s.scalars(select(Turma).where(Turma.periodo_letivo_id == periodo_id))
        ).all()
    }
    turmas_da_linha: dict[int, list[Turma]] = {}

    for linha in linhas:
        proposta = linha.turma_proposta or {}
        if not proposta.get("e_turma") or proposta.get("periodo_numero") is None:
            turmas_da_linha[linha.id] = []
            continue
        alvo: list[Turma] = []
        for curso_slug in proposta.get("cursos", []):
            curso = cursos.get(curso_slug)
            if curso is None:
                continue
            chave = (curso.id, proposta["turno"], proposta["periodo_numero"])
            turma = turmas.get(chave)
            if turma is None:
                turma = Turma(
                    periodo_letivo_id=periodo_id,
                    curso_id=curso.id,
                    turno=Turno(proposta["turno"]),
                    periodo_numero=proposta["periodo_numero"],
                    modulo=proposta.get("modulo"),
                    rotulos_origem=[],
                    abas_origem=[],
                    colunas_origem=[],
                    compartilhada_ciclo_basico=proposta.get(
                        "compartilhada_ciclo_basico", False
                    ),
                )
                s.add(turma)
                await s.flush()
                turmas[chave] = turma
                criados["turmas"] += 1
            # Acumula a procedência: a mesma turma vem de várias colunas (RN-04).
            _acumular(turma, "rotulos_origem", proposta.get("rotulo"))
            _acumular(turma, "abas_origem", proposta.get("aba"))
            _acumular(turma, "colunas_origem", proposta.get("referencia"))
            if proposta.get("modulo") and not turma.modulo:
                turma.modulo = proposta["modulo"]
            alvo.append(turma)
        turmas_da_linha[linha.id] = alvo

    await s.flush()

    # 5/6) ofertas e vínculos N:N
    ofertas = {
        (o.disciplina_id, o.professor_id): o
        for o in (
            await s.scalars(select(Oferta).where(Oferta.periodo_letivo_id == periodo_id))
        ).all()
    }
    vinculos = {
        (ot.oferta_id, ot.turma_id)
        for ot in (await s.scalars(select(OfertaTurma))).all()
    }
    ofertas_vistas: set[int] = set()
    alocacoes_novas: list[Alocacao] = []

    for linha in linhas:
        decisao = linha.decisao_admin or {}
        disc_id, prof_id = decisao.get("disciplina_id"), decisao.get("professor_id")
        if not disc_id or not prof_id:
            continue

        oferta = ofertas.get((disc_id, prof_id))
        if oferta is None:
            oferta = Oferta(
                periodo_letivo_id=periodo_id,
                disciplina_id=disc_id,
                professor_id=prof_id,
            )
            s.add(oferta)
            await s.flush()
            ofertas[(disc_id, prof_id)] = oferta
            criados["ofertas"] += 1
        elif not oferta.ativo:
            oferta.ativo = True
        ofertas_vistas.add(oferta.id)

        for turma in turmas_da_linha.get(linha.id, []):
            if (oferta.id, turma.id) not in vinculos:
                s.add(OfertaTurma(oferta_id=oferta.id, turma_id=turma.id))
                vinculos.add((oferta.id, turma.id))

        alocacoes_novas.append(
            Alocacao(
                oferta_id=oferta.id,
                turma_id=turmas_da_linha.get(linha.id, [None])[0].id
                if turmas_da_linha.get(linha.id)
                else None,
                dia_semana=_dia_para_numero(linha.dia_semana),
                horario_rotulo=linha.horario,
                duracao_horarios=linha.duracao_horarios or 1,
                modalidade=linha.modalidade_proposta or Modalidade.NAO_INFORMADA,
                aba_origem=linha.aba,
                celula_origem=linha.celula,
                texto_origem=linha.texto_origem,  # RN-11
            )
        )

    await s.flush()

    # 7) oferta sem nenhuma turma nasce não avaliável (RN-15)
    sem_turma = 0
    for oferta in ofertas.values():
        tem_turma = any(ot[0] == oferta.id for ot in vinculos)
        if not tem_turma:
            oferta.avaliavel = False
            sem_turma += 1

    # 8) alocações: substitui as do período inteiro
    ids_ofertas = [o.id for o in ofertas.values()]
    if ids_ofertas:
        await s.execute(delete(Alocacao).where(Alocacao.oferta_id.in_(ids_ofertas)))
    for a in alocacoes_novas:
        s.add(a)

    # 9) oferta ausente do arquivo é desativada, nunca apagada
    desativadas = 0
    for oferta in ofertas.values():
        if oferta.id not in ofertas_vistas and oferta.ativo:
            oferta.ativo = False
            desativadas += 1

    # 10) encerra a importação
    importacao.status = StatusImportacao.APLICADA
    importacao.aplicada_em = datetime.now(timezone.utc)

    await s.commit()
    return {
        **criados,
        "alocacoes": len(alocacoes_novas),
        "ofertas_sem_turma": sem_turma,
        "ofertas_desativadas": desativadas,
    }


def _acumular(turma: Turma, campo: str, valor: str | None) -> None:
    if not valor:
        return
    atual = list(getattr(turma, campo) or [])
    if valor not in atual:
        atual.append(valor)
        setattr(turma, campo, atual)


async def _garantir_alias_professor(s: AsyncSession, prof: Professor, texto: str) -> None:
    slug = slugificar(texto)
    if slug == prof.slug:
        return
    existe = await s.scalar(
        select(ProfessorAlias).where(ProfessorAlias.slug_origem == slug)
    )
    if existe is None:
        s.add(ProfessorAlias(professor_id=prof.id, texto_origem=texto, slug_origem=slug))


async def _garantir_alias_disciplina(
    s: AsyncSession, disc: Disciplina, texto: str
) -> None:
    slug = slugificar(texto)
    if slug == disc.slug:
        return
    existe = await s.scalar(
        select(DisciplinaAlias).where(DisciplinaAlias.slug_origem == slug)
    )
    if existe is None:
        s.add(
            DisciplinaAlias(disciplina_id=disc.id, texto_origem=texto, slug_origem=slug)
        )
