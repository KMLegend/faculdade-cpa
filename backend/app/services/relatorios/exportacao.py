"""Exportação CSV para o relatório oficial da CPA (doc 08 §3.9).

Uma linha por (oferta/instrumento, pergunta) com AGREGADOS — nunca uma linha
por submissão, que facilitaria reidentificação por cruzamento.

`codigo` e `equivalencia_id` são obrigatórias: sem elas a planilha não cruza
com a de outro ciclo sem casar por texto.
"""

from __future__ import annotations

import csv
import io

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Curso, DimensaoSinaes, Disciplina, EixoSinaes, Formulario, FormularioPergunta,
    Oferta, PeriodoLetivo, Professor, RespostaItem, Submissao, Turma,
)
from app.services.isg import agregar

COLUNAS = [
    "periodo", "segmento", "instrumento", "codigo", "equivalencia_id",
    "versao_texto", "eixo", "dimensao", "dimensao_nome", "curso", "turno",
    "turma", "disciplina", "professor", "bloco", "pergunta",
    "submissoes", "respostas", "media", "isg_pct", "mediana",
    "d1", "d2", "d3", "d4", "d5",
]


async def exportar_csv(periodo_letivo_id: int, s: AsyncSession) -> str:
    periodo = await s.get(PeriodoLetivo, periodo_letivo_id)
    dimensoes = {
        d.id: d for d in (await s.scalars(select(DimensaoSinaes))).all()
    }
    eixos = {e.id: e for e in (await s.scalars(select(EixoSinaes))).all()}

    linhas = (
        await s.execute(
            select(
                FormularioPergunta.codigo,
                FormularioPergunta.equivalencia_id,
                FormularioPergunta.versao_texto,
                FormularioPergunta.dimensao_id,
                FormularioPergunta.bloco,
                FormularioPergunta.texto_snapshot,
                FormularioPergunta.oferta_id,
                Formulario.segmento,
                Formulario.tipo_instrumento,
                Formulario.turma_id,
                RespostaItem.valor_numerico,
                Submissao.id,
            )
            .select_from(RespostaItem)
            .join(Submissao, Submissao.id == RespostaItem.submissao_id)
            .join(Formulario, Formulario.id == Submissao.formulario_id)
            .join(
                FormularioPergunta,
                FormularioPergunta.id == RespostaItem.formulario_pergunta_id,
            )
            .where(
                Formulario.periodo_letivo_id == periodo_letivo_id,
                RespostaItem.valor_numerico.isnot(None),
            )
        )
    ).all()

    # Contexto de oferta e turma, resolvido uma vez
    ofertas: dict[int, tuple[str, str]] = {}
    for oferta in (
        await s.scalars(
            select(Oferta).where(Oferta.periodo_letivo_id == periodo_letivo_id)
        )
    ).all():
        disc = await s.get(Disciplina, oferta.disciplina_id)
        prof = await s.get(Professor, oferta.professor_id)
        ofertas[oferta.id] = (
            disc.nome if disc else "",
            prof.nome_exibicao if prof else "",
        )

    turmas: dict[int, tuple[str, str, str]] = {}
    for turma in (
        await s.scalars(
            select(Turma).where(Turma.periodo_letivo_id == periodo_letivo_id)
        )
    ).all():
        curso = await s.get(Curso, turma.curso_id)
        turmas[turma.id] = (
            curso.nome if curso else "",
            turma.turno.value,
            f"{turma.periodo_numero}º período",
        )

    grupos: dict[tuple, dict] = {}
    for (
        codigo, equiv, versao, dim_id, bloco, texto, oferta_id,
        segmento, instrumento, turma_id, valor, sub_id,
    ) in linhas:
        chave = (codigo, oferta_id, turma_id)
        reg = grupos.setdefault(
            chave,
            {
                "codigo": codigo, "equivalencia_id": equiv, "versao_texto": versao,
                "dim_id": dim_id, "bloco": bloco.value, "pergunta": texto,
                "oferta_id": oferta_id, "segmento": segmento.value,
                "instrumento": instrumento.value, "turma_id": turma_id,
                "valores": [], "subs": set(),
            },
        )
        reg["valores"].append(valor)
        reg["subs"].add(sub_id)

    saida = io.StringIO()
    escritor = csv.DictWriter(saida, fieldnames=COLUNAS)
    escritor.writeheader()

    for reg in sorted(grupos.values(), key=lambda r: (r["codigo"], r["oferta_id"] or 0)):
        dim = dimensoes.get(reg["dim_id"])
        eixo = eixos.get(dim.eixo_id) if dim else None
        disciplina, professor = ofertas.get(reg["oferta_id"], ("", ""))
        curso, turno, turma = turmas.get(reg["turma_id"], ("", "", ""))
        a = agregar(reg["valores"])
        escritor.writerow(
            {
                "periodo": periodo.codigo if periodo else "",
                "segmento": reg["segmento"],
                "instrumento": reg["instrumento"],
                "codigo": reg["codigo"],
                "equivalencia_id": reg["equivalencia_id"],
                "versao_texto": reg["versao_texto"],
                "eixo": eixo.numero if eixo else "",
                "dimensao": dim.numero if dim else "",
                "dimensao_nome": (dim.nome_institucional or dim.nome) if dim else "",
                "curso": curso,
                "turno": turno,
                "turma": turma,
                "disciplina": disciplina,
                "professor": professor,
                "bloco": reg["bloco"],
                "pergunta": reg["pergunta"],
                "submissoes": len(reg["subs"]),
                "respostas": a.respostas,
                "media": a.media,
                "isg_pct": a.isg_pct,
                "mediana": a.mediana,
                **{f"d{n}": a.distribuicao[str(n)] for n in range(1, 6)},
            }
        )
    return saida.getvalue()
