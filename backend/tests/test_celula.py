"""Corpus do doc 03 §3.3 — 17 células literais de `horario 20262.xlsx`.

Cada caso aqui quebrou (ou quebraria) um parser ingênuo. São o contrato do
`celula.interpretar`.
"""

import pytest

from app.services.importador.celula import Modalidade, StatusLinha, interpretar

M = Modalidade

CORPUS = [
    # (texto da célula, disciplina, professor, modalidades, flags esperadas)
    ("Imunologia - Prof Clayson", "Imunologia", "Clayson", [], []),
    (
        "Bioquímica (Preleção) - Profa Andrea",
        "Bioquímica", "Andrea", [M.PRELECAO], [],
    ),
    ("Bioética -Prof Rogério", "Bioética", "Rogério", [], []),
    (
        "Histologia e Embriologia (Preleção)- Prof  Prof André",
        "Histologia e Embriologia", "André", [M.PRELECAO], ["PREFIXO_DUPLICADO"],
    ),
    (
        "Caso Problematizador e Avaliação Interdisciplinar P - (Profa Isabela)",
        "Caso Problematizador e Avaliação Interdisciplinar P", "Isabela", [], [],
    ),
    (
        "Promoção da Saúde - Régis",
        "Promoção da Saúde", "Régis", [], ["SEM_PREFIXO_PROF"],
    ),
    (
        "Caso Problematizador e Avaliação Interdisciplinar EF - Profa Lisiane (Extensão)",
        "Caso Problematizador e Avaliação Interdisciplinar EF", "Lisiane",
        [M.EXTENSAO], [],
    ),
    (
        "Instrumentos Básicos de Enfermagem (Prática Hospitalar) - Prof Luciene",
        "Instrumentos Básicos de Enfermagem", "Luciene", [M.PRATICA_HOSPITALAR], [],
    ),
    (
        "Práticas Biomédicas - Química (Prática) - Prof Alexandre",
        "Práticas Biomédicas - Química", "Alexandre", [M.PRATICA], ["HIFEN_NO_NOME"],
    ),
    (
        "Ecologia, análises físico-químicas e microbiológicas em saneamento ambiental "
        "(Prática) - Profa Vanessa",
        "Ecologia, análises físico-químicas e microbiológicas em saneamento ambiental",
        "Vanessa", [M.PRATICA], ["HIFEN_NO_NOME"],
    ),
    (
        "Optativa I ou II - Endocrinologia laboratorial - Prof Roberpaulo",
        "Optativa I ou II - Endocrinologia laboratorial", "Roberpaulo", [],
        ["DISCIPLINA_AMBIGUA_OU", "HIFEN_NO_NOME"],
    ),
    (
        "Estágio Supervisionado I ou II (Prof Washington)",
        "Estágio Supervisionado I ou II", "Washington", [], ["DISCIPLINA_AMBIGUA_OU"],
    ),
    (
        "TCC 1 ou TCC 2 (Prof Clayson)",
        "TCC 1 ou TCC 2", "Clayson", [], ["DISCIPLINA_AMBIGUA_OU"],
    ),
    (
        "Toxicologia - Preleção - Prof Washignton",
        "Toxicologia", "Washignton", [M.PRELECAO], ["MODALIDADE_SEM_PARENTESES"],
    ),
    (
        "Estudos Disciplinares e Projeto Integrador II- Prof Leonardo (EAD",
        "Estudos Disciplinares e Projeto Integrador II", "Leonardo", [M.EAD],
        ["PARENTESE_NAO_FECHADO"],
    ),
    (
        "O cuidar nos Processos Críticos - Preceptor (A contratar) - "
        "Lançar no nome da Profa Katiulcy",
        None, None, [], ["OBSERVACAO_ADMINISTRATIVA"],
    ),
]


@pytest.mark.parametrize(
    "texto,disciplina,professor,modalidades,flags",
    CORPUS,
    ids=[c[0][:42] for c in CORPUS],
)
def test_corpus(texto, disciplina, professor, modalidades, flags):
    aula = interpretar(texto)
    assert aula is not None, "célula do corpus não deveria ser descartada"
    if disciplina is not None:
        assert aula.disciplina == disciplina
    assert aula.professor == professor
    assert aula.modalidades == modalidades
    for f in flags:
        assert f in aula.flags, f"faltou a flag {f}: {aula.flags}"


def test_celula_lixo_descartada():
    for lixo in (".", "", None, "Turma A", "Segunda-feira", "1º Horário - 07:30",
                 "Sub - Turma B", "* Matricular 1, 2, 3, 4 períodos"):
        assert interpretar(lixo) is None


class TestStatus:
    def test_ok(self):
        assert interpretar("Imunologia - Prof Clayson").status is StatusLinha.OK

    def test_revisar_disciplina_ambigua(self):
        assert interpretar("TCC 1 ou TCC 2 (Prof Clayson)").status is StatusLinha.REVISAR

    def test_revisar_sem_prefixo(self):
        assert interpretar("Promoção da Saúde - Régis").status is StatusLinha.REVISAR

    def test_erro_bilhete_administrativo(self):
        aula = interpretar(
            "O cuidar nos Processos Críticos - Preceptor (A contratar) - "
            "Lançar no nome da Profa Katiulcy"
        )
        assert aula.status is StatusLinha.ERRO

    def test_flags_informativas_nao_bloqueiam(self):
        aula = interpretar("Histologia e Embriologia (Preleção)- Prof  Prof André")
        assert "PREFIXO_DUPLICADO" in aula.flags
        assert aula.status is StatusLinha.OK
