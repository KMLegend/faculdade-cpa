"""Casamento de texto da planilha com o cadastro existente (doc 03 §4).

A ordem é sempre a mesma — para no primeiro que casar:

  1. alias já conciliado           → 1.00, vincula
  2. slug idêntico                 → 1.00, vincula
  3. similaridade ≥ 0.80           → score, SUGERE (exige revisão)
  4. nada                          → 0.00, entidade nova (exige revisão)

⚠️ **Fuzzy nunca vincula sozinho.** O doc 03 §4 previa vincular automaticamente
acima de 0,95, mas medir contra o arquivo real mostrou que isso é inseguro:

    0,971  "Caso Problematizador … Interdisciplinar P"  ←→  "… Interdisciplinar M"
    0,978  "Estudos Disciplinares e Projeto Integrador II"  ←→  "… Integrador IV"

São disciplinas DIFERENTES, de módulos e cursos distintos, que diferem em uma ou
duas letras finais de um nome longo. Em contrapartida `washignton`→`washington`
dá apenas 0,900, porque em nome curto uma transposição pesa muito mais.

A razão de similaridade é cega ao que distingue dois nomes: ela mede o quanto se
parecem, não se significam a mesma coisa. Por isso o fuzzy aqui só SUGERE — quem
funde é a pessoa, e a decisão vira alias para não se repetir.

Usa `difflib.SequenceMatcher` da biblioteca padrão: a restrição de pacotes leves
de `01-init` não comporta dependência de fuzzy matching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.texto import slugificar
from app.models import (
    Curso, Disciplina, DisciplinaAlias, Oferta, OfertaTurma, Professor,
    ProfessorAlias, Turma,
)

#: Abaixo disto, nem sugere — trata como entidade nova.
LIMIAR_SUGESTAO = 0.80
#: Acima disto a sugestão aparece em destaque na conciliação, mas continua
#: exigindo confirmação humana. Vincular sozinho fundiria disciplinas distintas.
LIMIAR_ALTA_CONFIANCA = 0.95


class Etapa(str, Enum):
    ALIAS = "ALIAS"
    EXATO = "EXATO"
    #: Sugestão forte (≥ 0,95) — ainda assim exige confirmação.
    FUZZY_ALTA = "FUZZY_ALTA"
    FUZZY_SUGESTAO = "FUZZY_SUGESTAO"
    NOVO = "NOVO"


@dataclass
class Resultado:
    """O que o matching concluiu sobre um texto da planilha."""

    texto: str
    slug: str
    etapa: Etapa
    entidade_id: int | None = None
    nome_sugerido: str | None = None
    confianca: float = 0.0
    motivos: list[str] = field(default_factory=list)

    #: Só alias e slug idêntico vinculam sem pessoa no meio.
    VINCULA_SOZINHO = (Etapa.ALIAS, Etapa.EXATO)

    @property
    def precisa_revisao(self) -> bool:
        return self.etapa not in self.VINCULA_SOZINHO or bool(self.motivos)


def similaridade(a: str, b: str) -> float:
    """0..1 entre dois slugs. `difflib`, sem dependência externa."""
    return SequenceMatcher(None, a, b).ratio()


def _melhor_candidato(
    slug: str, candidatos: dict[str, tuple[int, str]]
) -> tuple[float, int | None, str | None]:
    """Candidato mais parecido: (score, id, nome)."""
    melhor_score, melhor_id, melhor_nome = 0.0, None, None
    for slug_candidato, (id_, nome) in candidatos.items():
        s = similaridade(slug, slug_candidato)
        if s > melhor_score:
            melhor_score, melhor_id, melhor_nome = s, id_, nome
    return melhor_score, melhor_id, melhor_nome


class Catalogo:
    """Cadastro carregado uma vez por importação.

    Consultar o banco por linha faria ~164 × 4 consultas; carregar tudo de uma
    vez cabe em memória (dezenas de registros) e deixa o matching puro.
    """

    def __init__(self) -> None:
        self.professores: dict[str, tuple[int, str]] = {}
        self.disciplinas: dict[str, tuple[int, str]] = {}
        self.alias_professor: dict[str, int] = {}
        self.alias_disciplina: dict[str, int] = {}
        #: professor_id → {curso_slug} — base da checagem de homônimos (RN-14)
        self.cursos_do_professor: dict[int, set[str]] = {}

    @classmethod
    async def carregar(cls, s: AsyncSession, periodo_letivo_id: int) -> Catalogo:
        c = cls()
        for p in (await s.scalars(select(Professor))).all():
            c.professores[p.slug] = (p.id, p.nome_exibicao)
        for d in (await s.scalars(select(Disciplina))).all():
            c.disciplinas[d.slug] = (d.id, d.nome)
        for a in (await s.scalars(select(ProfessorAlias))).all():
            c.alias_professor[a.slug_origem] = a.professor_id
        for a in (await s.scalars(select(DisciplinaAlias))).all():
            c.alias_disciplina[a.slug_origem] = a.disciplina_id

        # Em que cursos (por SLUG) cada professor já leciona neste período.
        # Guardar o id aqui e comparar com slug adiante marcaria todo professor
        # como homônimo — foi o defeito que quebrou a reimportação.
        linhas = (
            await s.execute(
                select(Oferta.professor_id, Curso.slug)
                .join(Oferta.ofertas_turma)
                .join(Turma, Turma.id == OfertaTurma.turma_id)
                .join(Curso, Curso.id == Turma.curso_id)
                .where(Oferta.periodo_letivo_id == periodo_letivo_id)
                .distinct()
            )
        ).all()
        for professor_id, curso_slug in linhas:
            c.cursos_do_professor.setdefault(professor_id, set()).add(curso_slug)
        return c

    @property
    def cadastro_vazio(self) -> bool:
        """Primeira importação: habilita a criação em lote (doc 03 §4.1)."""
        return not self.professores and not self.disciplinas

    # ── casamento ────────────────────────────────────────────────────────────
    def casar_professor(
        self, texto: str, cursos_da_coluna: list[str] | None = None
    ) -> Resultado:
        """RN-14 — homônimo entre cursos nunca é fundido automaticamente.

         traz TODOS os cursos que a coluna atende: uma coluna
        de ciclo básico serve Biomedicina e Enfermagem ao mesmo tempo, e usar só
        o primeiro acusaria homônimo onde não há.
        """
        r = self._casar(texto, self.alias_professor, self.professores)
        if (
            r.entidade_id is not None
            and cursos_da_coluna
            and r.etapa in Resultado.VINCULA_SOZINHO
        ):
            conhecidos = self.cursos_do_professor.get(r.entidade_id, set())
            # Só é homônimo se o professor NÃO leciona em nenhum dos cursos
            # desta coluna — havendo interseção, é a mesma pessoa.
            if conhecidos and not conhecidos & set(cursos_da_coluna):
                r.motivos.append("HOMONIMO_ENTRE_CURSOS")
        return r

    def casar_disciplina(self, texto: str) -> Resultado:
        return self._casar(texto, self.alias_disciplina, self.disciplinas)

    def _casar(
        self,
        texto: str,
        aliases: dict[str, int],
        catalogo: dict[str, tuple[int, str]],
    ) -> Resultado:
        slug = slugificar(texto or "")
        base = {"texto": texto, "slug": slug}

        if not slug:
            return Resultado(**base, etapa=Etapa.NOVO, motivos=["TEXTO_VAZIO"])

        # 1) alias já conciliado em ciclo anterior
        if slug in aliases:
            id_ = aliases[slug]
            nome = next((n for i, n in catalogo.values() if i == id_), None)
            return Resultado(
                **base, etapa=Etapa.ALIAS, entidade_id=id_,
                nome_sugerido=nome, confianca=1.0,
            )

        # 2) slug idêntico
        if slug in catalogo:
            id_, nome = catalogo[slug]
            return Resultado(
                **base, etapa=Etapa.EXATO, entidade_id=id_,
                nome_sugerido=nome, confianca=1.0,
            )

        # 3) aproximado — SUGERE, nunca vincula sozinho
        score, id_, nome = _melhor_candidato(slug, catalogo)
        if score >= LIMIAR_SUGESTAO:
            alta = score >= LIMIAR_ALTA_CONFIANCA
            return Resultado(
                **base,
                etapa=Etapa.FUZZY_ALTA if alta else Etapa.FUZZY_SUGESTAO,
                entidade_id=id_,
                nome_sugerido=nome,
                confianca=round(score, 3),
                motivos=["MATCH_FUZZY"],
            )

        # 4) entidade nova
        return Resultado(**base, etapa=Etapa.NOVO, confianca=0.0)


def agrupar_por_similaridade(textos: list[str]) -> list[list[str]]:
    """Agrupa grafias parecidas DENTRO do próprio arquivo (doc 03 §4.1).

    É assim que `Washignton`/`Washington` e `Vitória`/`Victória` aparecem para
    decisão já na primeira carga, quando o cadastro ainda está vazio e não há
    com o que comparar.
    """
    restantes = sorted({t for t in textos if t})
    grupos: list[list[str]] = []
    while restantes:
        base = restantes.pop(0)
        grupo = [base]
        slug_base = slugificar(base)
        for outro in list(restantes):
            if similaridade(slug_base, slugificar(outro)) >= LIMIAR_SUGESTAO:
                grupo.append(outro)
                restantes.remove(outro)
        if len(grupo) > 1:
            grupos.append(sorted(grupo))
    return grupos
