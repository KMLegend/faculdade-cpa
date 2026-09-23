"""Interpretação da célula de aula da planilha de grade (doc 03 §3).

Função pura, sem I/O: recebe o texto bruto de uma célula e devolve a disciplina,
o professor, as modalidades e as marcas (`flags`) que a conciliação usará.

A gramática observada na planilha real:

    <disciplina> [ "(" <modalidade> ")" ] <sep> [ "(" ] <prefixo> <nome> [ ")" ] [ "(" <sufixo> ")" ]

O corpus de teste está em tests/test_celula.py — 17 células literais do arquivo
`horario 20262.xlsx`, incluindo os casos que quebram parsers ingênuos.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class Modalidade(str, Enum):
    PRELECAO = "PRELECAO"
    PRATICA = "PRATICA"
    PRATICA_HOSPITALAR = "PRATICA_HOSPITALAR"
    EAD = "EAD"
    EXTENSAO = "EXTENSAO"
    ESTAGIO = "ESTAGIO"


class StatusLinha(str, Enum):
    OK = "OK"
    REVISAR = "REVISAR"
    ERRO = "ERRO"
    IGNORADA = "IGNORADA"


# Flags que impedem o commit (doc 03 §3.4)
FLAGS_ERRO = {
    "PROFESSOR_NAO_IDENTIFICADO",
    "OBSERVACAO_ADMINISTRATIVA",
    "DISCIPLINA_VAZIA",
}
FLAGS_REVISAR = {
    "DISCIPLINA_AMBIGUA_OU",
    "SEM_PREFIXO_PROF",
}


@dataclass
class Aula:
    disciplina: str | None
    professor: str | None
    modalidades: list[Modalidade] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    texto_origem: str = ""

    @property
    def status(self) -> StatusLinha:
        if any(f in FLAGS_ERRO for f in self.flags):
            return StatusLinha.ERRO
        if any(f in FLAGS_REVISAR for f in self.flags):
            return StatusLinha.REVISAR
        return StatusLinha.OK


# ─── ruído: cabeçalhos, dias da semana, rótulos ──────────────────────────────
_RUIDO = re.compile(
    r"^(Turma|Sub ?- ?Turma|\*? ?Matricular|\d+\s*[ºo°]?\s*(PER|Período)"
    r"|[A-Za-zÀ-ú]+-feira|Sábado|Extras|Práticas Hospitalares|Matutino|Noturno"
    r"|\d+[ºo°]?\s*Horário)",
    re.IGNORECASE,
)

_MODALIDADES = {
    "prelecao": Modalidade.PRELECAO,
    "pratica": Modalidade.PRATICA,
    "pratica hospitalar": Modalidade.PRATICA_HOSPITALAR,
    "ead": Modalidade.EAD,
    "extensao": Modalidade.EXTENSAO,
    "estagio": Modalidade.ESTAGIO,
}
_TAG = re.compile(
    r"\(\s*(Prele[çc][ãa]o|Pr[áa]tica\s+Hospitalar|Pr[áa]tica|EAD[^)]*"
    r"|Extens[ãa]o|Est[áa]gio)\s*\)?",
    re.IGNORECASE,
)
# "Toxicologia - Preleção - Prof X": modalidade sem parênteses
_TAG_SOLTA = re.compile(
    r"\s*[-–]\s*(Prele[çc][ãa]o|Pr[áa]tica\s+Hospitalar|Pr[áa]tica)\s*(?=[-–])",
    re.IGNORECASE,
)
_LIXO = re.compile(r"\(\s*(\d+\s*hrs?|EAD[^)]*|Extens[ãa]o)\s*\)?", re.IGNORECASE)
_ADMIN = re.compile(r"preceptor|a contratar|lançar no nome", re.IGNORECASE)


def _normalizar_modalidade(bruto: str) -> Modalidade | None:
    import unicodedata

    t = unicodedata.normalize("NFKD", bruto.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z ]+", "", t).strip()
    # Casar do prefixo mais LONGO para o mais curto: "pratica hospitalar"
    # não pode ser capturado por "pratica".
    for chave in sorted(_MODALIDADES, key=len, reverse=True):
        if t.startswith(chave):
            return _MODALIDADES[chave]
    return None


def interpretar(texto: str | None) -> Aula | None:
    """Interpreta uma célula. Devolve None se for ruído ou vazia."""
    if not texto:
        return None
    bruto = re.sub(r"\s+", " ", str(texto)).strip()
    if len(bruto) < 6 or bruto == "." or _RUIDO.match(bruto):
        return None

    flags: list[str] = []
    modalidades: list[Modalidade] = []

    if _ADMIN.search(bruto):
        flags.append("OBSERVACAO_ADMINISTRATIVA")

    corpo = bruto
    for m in _TAG.finditer(corpo):
        mod = _normalizar_modalidade(m.group(1))
        if mod and mod not in modalidades:
            modalidades.append(mod)
    corpo = _TAG.sub(" ", corpo)

    for m in _TAG_SOLTA.finditer(corpo):
        mod = _normalizar_modalidade(m.group(1))
        if mod and mod not in modalidades:
            modalidades.append(mod)
            flags.append("MODALIDADE_SEM_PARENTESES")
    corpo = _TAG_SOLTA.sub(" ", corpo)

    if "(EAD" in bruto and ")" not in bruto[bruto.index("(EAD") :]:
        flags.append("PARENTESE_NAO_FECHADO")
        if Modalidade.EAD not in modalidades:
            modalidades.append(Modalidade.EAD)

    corpo = _LIXO.sub(" ", corpo)
    corpo = re.sub(r"\s+", " ", corpo).strip(" -–.")

    professor, disciplina = _extrair_professor(corpo, flags)

    if professor is None:
        flags.append("PROFESSOR_NAO_IDENTIFICADO")
        return Aula(None, None, modalidades, flags, bruto)

    disciplina = re.sub(r"\s+", " ", disciplina).strip(" -–.")
    if not disciplina:
        flags.append("DISCIPLINA_VAZIA")
    if " ou " in f" {disciplina.lower()} ":
        flags.append("DISCIPLINA_AMBIGUA_OU")
    if re.search(r"[-–]", disciplina):
        flags.append("HIFEN_NO_NOME")

    return Aula(disciplina or None, professor, modalidades, flags, bruto)


_NOME = r"([A-ZÀ-Ú][\wÀ-ú]+)"


def _extrair_professor(corpo: str, flags: list[str]) -> tuple[str | None, str]:
    """Localiza o professor no fim da célula (doc 03 §3.2, passo 4)."""
    # a) "(Prof<a> Nome)" no fim — "TCC 1 ou TCC 2 (Prof Clayson)"
    m = re.search(rf"\(\s*Prof[a]?\.?\s+{_NOME}\s*\)\s*$", corpo)
    if m:
        return m.group(1), corpo[: m.start()]

    # b) "- Prof<a> Nome" no fim — caso dominante. Tolera "Prof  Prof André"
    #    e parêntese só de um lado: "- (Profa Isabela)".
    m = re.search(
        rf"[-–]\s*\(?\s*(?:Prof[a]?\.?\s*)+{_NOME}\s*\)?\s*$", corpo
    )
    if m:
        antes = corpo[m.start() : m.end()]
        if len(re.findall(r"Prof", antes)) > 1:
            flags.append("PREFIXO_DUPLICADO")
        return m.group(1), corpo[: m.start()]

    # c) "- Nome" no fim, sem prefixo — "Promoção da Saúde - Régis"
    m = re.search(rf"[-–]\s*\(?\s*{_NOME}\s*\)?\s*$", corpo)
    if m and len(m.group(1)) > 2:
        flags.append("SEM_PREFIXO_PROF")
        return m.group(1), corpo[: m.start()]

    return None, corpo
