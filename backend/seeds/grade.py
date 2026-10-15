"""Seed da grade 2026.2 (17 turmas, 105 ofertas, 136 vínculos turma-oferta).

Idempotente — lê o fixture `grade_20262_esperado.json` e popula as tabelas
acadêmicas para o período letivo 2026.2.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import obter_settings
from app.core.texto import slugificar
from app.db.session import SessaoLocal
from app.models import (
    Curso, Disciplina, Oferta, OfertaTurma, PeriodoLetivo, Professor, Turma,
    Turno,
)

FIXTURE_GRADE = (
    obter_settings().caminho_anexos / "grade_20262_esperado.json"
)


async def semear_grade_20262(s: AsyncSession) -> dict[str, int]:
    dados = json.loads(FIXTURE_GRADE.read_text("utf-8"))

    # 1. Período Letivo
    codigo_periodo = dados.get("periodo_letivo", "2026.2")
    partes = codigo_periodo.split(".")
    ano, semestre = int(partes[0]), int(partes[1])
    periodo = await s.scalar(
        select(PeriodoLetivo).where(PeriodoLetivo.codigo == codigo_periodo)
    )
    if periodo is None:
        periodo = PeriodoLetivo(
            codigo=codigo_periodo, ano=ano, semestre=semestre, ativo=True
        )
        s.add(periodo)
        await s.flush()

    # 2. Cursos
    cursos_db = (await s.scalars(select(Curso))).all()
    cursos_por_slug = {c.slug: c.id for c in cursos_db}

    # 3. Turmas (17)
    turmas_map: dict[int, Turma] = {}
    turmas_criadas = 0
    for t in dados["turmas"]:
        curso_id = cursos_por_slug[t["curso"]]
        turno = Turno(t["turno"])
        periodo_num = t["periodo_numero"]

        turma = await s.scalar(
            select(Turma).where(
                Turma.periodo_letivo_id == periodo.id,
                Turma.curso_id == curso_id,
                Turma.turno == turno,
                Turma.periodo_numero == periodo_num,
            )
        )
        if turma is None:
            turma = Turma(
                periodo_letivo_id=periodo.id,
                curso_id=curso_id,
                turno=turno,
                periodo_numero=periodo_num,
                modulo=", ".join(t.get("modulos", [])) or None,
                rotulos_origem=t.get("rotulos_origem"),
                colunas_origem=t.get("colunas_origem"),
                compartilhada_ciclo_basico=t.get(
                    "turma_compartilhada_ciclo_basico", False
                ),
                ativo=True,
            )
            s.add(turma)
            await s.flush()
            turmas_criadas += 1
        turmas_map[t["id"]] = turma

    # 4. Professores e Disciplinas dos dados de oferta
    professores_map: dict[str, int] = {}
    disciplinas_map: dict[str, int] = {}

    for of in dados["ofertas"]:
        p_nome = of["professor"]
        p_slug = slugificar(p_nome)
        if p_slug not in professores_map:
            prof = await s.scalar(
                select(Professor).where(Professor.slug == p_slug)
            )
            if prof is None:
                prof = Professor(nome_exibicao=p_nome, slug=p_slug, ativo=True)
                s.add(prof)
                await s.flush()
            professores_map[p_slug] = prof.id

        d_nome = of["disciplina"]
        d_slug = slugificar(d_nome)
        if d_slug not in disciplinas_map:
            disc = await s.scalar(
                select(Disciplina).where(Disciplina.slug == d_slug)
            )
            if disc is None:
                disc = Disciplina(nome=d_nome, slug=d_slug, ativo=True)
                s.add(disc)
                await s.flush()
            disciplinas_map[d_slug] = disc.id

    # 5. Ofertas (105) e OfertaTurma
    ofertas_criadas = 0
    vinculos_criados = 0
    for of in dados["ofertas"]:
        p_slug = slugificar(of["professor"])
        d_slug = slugificar(of["disciplina"])
        prof_id = professores_map[p_slug]
        disc_id = disciplinas_map[d_slug]

        oferta = await s.scalar(
            select(Oferta).where(
                Oferta.periodo_letivo_id == periodo.id,
                Oferta.disciplina_id == disc_id,
                Oferta.professor_id == prof_id,
            )
        )
        avaliavel = of["qtd_turmas"] > 0
        if oferta is None:
            oferta = Oferta(
                periodo_letivo_id=periodo.id,
                disciplina_id=disc_id,
                professor_id=prof_id,
                avaliavel=avaliavel,
                ativo=True,
            )
            s.add(oferta)
            await s.flush()
            ofertas_criadas += 1
        else:
            if oferta.avaliavel != avaliavel:
                oferta.avaliavel = avaliavel
                await s.flush()

        for tid in of.get("turmas", []):
            turma_obj = turmas_map.get(tid)
            if turma_obj:
                vinculo = await s.scalar(
                    select(OfertaTurma).where(
                        OfertaTurma.oferta_id == oferta.id,
                        OfertaTurma.turma_id == turma_obj.id,
                    )
                )
                if vinculo is None:
                    vinculo = OfertaTurma(
                        oferta_id=oferta.id, turma_id=turma_obj.id
                    )
                    s.add(vinculo)
                    vinculos_criados += 1

    await s.flush()

    # Ressincronizar sequences
    for tabela in ("turma", "disciplina", "professor", "oferta", "oferta_turma"):
        try:
            await s.execute(
                text(
                    f"SELECT setval(pg_get_serial_sequence('{tabela}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {tabela}), 1))"
                )
            )
        except Exception:
            pass

    return {
        "turmas": len(turmas_map),
        "turmas_criadas": turmas_criadas,
        "ofertas": len(dados["ofertas"]),
        "ofertas_criadas": ofertas_criadas,
        "vinculos": vinculos_criados,
    }


async def main() -> None:
    async with SessaoLocal() as s:
        resumo = await semear_grade_20262(s)
        await s.commit()
    print("Grade 2026.2 semeada:", resumo)


if __name__ == "__main__":
    asyncio.run(main())
