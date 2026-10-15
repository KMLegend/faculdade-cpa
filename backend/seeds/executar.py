"""Aplica os seeds: referência SINAES, cursos, equivalências e as 163 perguntas.

Idempotente — rodar duas vezes não duplica nada. O banco de perguntas vem do
Anexo B (`B_banco_perguntas_cpa.json`), que é o instrumento real da CPA, não uma
proposta desta especificação.

Uso:  python -m seeds.executar
"""

from __future__ import annotations

import asyncio
import json

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import obter_settings
from app.core.texto import slugificar
from app.db.session import SessaoLocal
from app.models import (
    AplicacaoPergunta, BlocoPergunta, Curso, DimensaoSinaes, Disciplina,
    DisciplinaAlias, EixoSinaes, EquivalenciaPergunta, Pergunta, Professor,
    ProfessorAlias, TipoInstrumento, TipoPergunta,
)
from seeds.aliases import ALIAS_DISCIPLINA, ALIAS_PROFESSOR
from seeds.cursos import CURSOS
from seeds.sinaes import DIMENSOES, EIXOS

BANCO_PERGUNTAS = obter_settings().caminho_anexos / "B_banco_perguntas_cpa.json"

INSTRUMENTO_DO_SEGMENTO = {
    "DISCENTE": TipoInstrumento.DISCENTE_TURMA,
    "DOCENTE": TipoInstrumento.DOCENTE,
    "TECNICO_ADMINISTRATIVO": TipoInstrumento.TECNICO_ADMINISTRATIVO,
    "COMUNIDADE": TipoInstrumento.COMUNIDADE,
}
#: Duplicatas detectadas no Anexo B §B.6 — mesmo texto, mesmo questionário.
CODIGOS_DUPLICADOS = {29, 86}


async def semear_sinaes(s: AsyncSession) -> dict[int, int]:
    """Devolve {numero_da_dimensao: id}."""
    por_numero_eixo: dict[int, int] = {}
    for numero, nome in EIXOS:
        eixo = await s.scalar(select(EixoSinaes).where(EixoSinaes.numero == numero))
        if eixo is None:
            eixo = EixoSinaes(numero=numero, nome=nome)
            s.add(eixo)
            await s.flush()
        por_numero_eixo[numero] = eixo.id

    por_numero_dim: dict[int, int] = {}
    for numero, nome, eixo_num in DIMENSOES:
        dim = await s.scalar(
            select(DimensaoSinaes).where(DimensaoSinaes.numero == numero)
        )
        if dim is None:
            dim = DimensaoSinaes(
                numero=numero,
                nome=nome,
                eixo_id=por_numero_eixo[eixo_num],
                # A CPA usa a nomenclatura legal; se mudar, é aqui.
                nome_institucional=nome,
                ordem_exibicao=numero,
            )
            s.add(dim)
            await s.flush()
        por_numero_dim[numero] = dim.id
    return por_numero_dim


async def semear_cursos(s: AsyncSession) -> dict[str, int]:
    por_slug: dict[str, int] = {}
    for slug, nome in CURSOS:
        curso = await s.scalar(select(Curso).where(Curso.slug == slug))
        if curso is None:
            curso = Curso(slug=slug, nome=nome)
            s.add(curso)
            await s.flush()
        por_slug[slug] = curso.id
    return por_slug


async def semear_perguntas(s: AsyncSession, dims: dict[int, int]) -> dict[str, int]:
    dados = json.loads(BANCO_PERGUNTAS.read_text("utf-8"))

    # ── equivalências: 67 grupos ────────────────────────────────────────────
    por_equiv: dict[int, int] = {}
    for grupo in dados["equivalencias"]:
        numero = grupo["equivalencia_id"]
        existente = await s.scalar(
            select(EquivalenciaPergunta).where(EquivalenciaPergunta.id == numero)
        )
        if existente is None:
            eq = EquivalenciaPergunta(
                id=numero,
                rotulo=grupo["texto"][:240],
                dimensao_id=dims[grupo["dimensao"]],
            )
            s.add(eq)
            await s.flush()
            por_equiv[numero] = eq.id
        else:
            por_equiv[numero] = existente.id

    # ── 163 perguntas ───────────────────────────────────────────────────────
    criadas = 0
    for q in dados["questoes"]:
        codigo = q["codigo"]
        if await s.scalar(select(Pergunta).where(Pergunta.codigo == codigo)):
            continue
        bloco = BlocoPergunta(q["bloco"])
        s.add(
            Pergunta(
                codigo=codigo,
                texto=q["questao"],
                equivalencia_id=por_equiv[q["equivalencia_id"]],
                dimensao_id=dims[q["dim"]],
                tipo_instrumento=INSTRUMENTO_DO_SEGMENTO[q["segmento"]],
                bloco=bloco,
                aplicacao=AplicacaoPergunta.TODAS,
                tipo=TipoPergunta.LIKERT_5,
                obrigatoria=True,
                ordem_exibicao=codigo,
                ativo=codigo not in CODIGOS_DUPLICADOS,
            )
        )
        criadas += 1
    await s.flush()
    return {"equivalencias": len(por_equiv), "perguntas": criadas}


async def ressincronizar_sequences(s: AsyncSession) -> None:
    """Realinha as sequences das tabelas semeadas com id explícito.

    Inserir com PK explícito NÃO avança a sequence no Postgres: o próximo
    INSERT sem id tentaria 1 e colidiria. Sem isto, criar a primeira pergunta
    nova pelo painel quebra com UniqueViolation.
    """
    for tabela in ("equivalencia_pergunta", "eixo_sinaes", "dimensao_sinaes"):
        await s.execute(
            text(
                f"SELECT setval(pg_get_serial_sequence('{tabela}', 'id'), "
                f"COALESCE((SELECT MAX(id) FROM {tabela}), 1))"
            )
        )


async def semear_aliases(s: AsyncSession) -> dict[str, int]:
    """Cria professor/disciplina canônicos e seus aliases conhecidos."""
    n_prof = n_disc = 0
    for slug_origem, nome_canonico in ALIAS_PROFESSOR.items():
        slug = slugificar(nome_canonico)
        prof = await s.scalar(select(Professor).where(Professor.slug == slug))
        if prof is None:
            prof = Professor(nome_exibicao=nome_canonico, slug=slug)
            s.add(prof)
            await s.flush()
        if not await s.scalar(
            select(ProfessorAlias).where(ProfessorAlias.slug_origem == slug_origem)
        ):
            s.add(
                ProfessorAlias(
                    professor_id=prof.id,
                    texto_origem=slug_origem,
                    slug_origem=slug_origem,
                )
            )
            n_prof += 1

    for slug_origem, nome_canonico in ALIAS_DISCIPLINA.items():
        slug = slugificar(nome_canonico)
        disc = await s.scalar(select(Disciplina).where(Disciplina.slug == slug))
        if disc is None:
            disc = Disciplina(nome=nome_canonico, slug=slug)
            s.add(disc)
            await s.flush()
        if not await s.scalar(
            select(DisciplinaAlias).where(DisciplinaAlias.slug_origem == slug_origem)
        ):
            s.add(
                DisciplinaAlias(
                    disciplina_id=disc.id,
                    texto_origem=slug_origem,
                    slug_origem=slug_origem,
                )
            )
            n_disc += 1
    await s.flush()
    return {"alias_professor": n_prof, "alias_disciplina": n_disc}


async def main() -> None:
    async with SessaoLocal() as s:
        dims = await semear_sinaes(s)
        cursos = await semear_cursos(s)
        perguntas = await semear_perguntas(s, dims)
        aliases = await semear_aliases(s)
        await ressincronizar_sequences(s)
        await s.commit()

    print("Seeds aplicados:")
    print(f"  eixos SINAES        : {len(EIXOS)}")
    print(f"  dimensões SINAES    : {len(dims)}")
    print(f"  cursos              : {len(cursos)}")
    print(f"  equivalências       : {perguntas['equivalencias']}")
    print(f"  perguntas criadas   : {perguntas['perguntas']}")
    print(f"  aliases professor   : {aliases['alias_professor']}")
    print(f"  aliases disciplina  : {aliases['alias_disciplina']}")


if __name__ == "__main__":
    asyncio.run(main())
