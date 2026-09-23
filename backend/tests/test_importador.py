"""Aceite do importador (doc 03 §6) contra a planilha real de 2026.2.

O fixture `grade_20262_esperado.json` é gerado por
`scripts/gerar_fixture_grade.py` a partir deste mesmo leitor — estes testes
travam o comportamento para que uma regressão apareça, não para provar o
fixture.
"""

import json
from pathlib import Path

import pytest

from app.core.texto import slugificar
from app.services.importador.leitor_xlsx import ler

ANEXOS = Path(__file__).resolve().parents[2] / ".agent/02-especificacao/anexos"
PLANILHA = ANEXOS / "horario_20262.xlsx"

ALIAS_PROFESSOR = {"washignton": "washington", "vitoria": "victoria"}
ALIAS_DISCIPLINA = {
    "cinnesiologia e biomecanica": "cinesiologia e biomecanica",
    "promocao a saude": "promocao da saude",
    "gestao de projetos em tecnologia de informacao": (
        "gestao de projetos em tecnologia da informacao"
    ),
}


def _canon(texto, aliases):
    s = slugificar(texto or "")
    return aliases.get(s, s)


@pytest.fixture(scope="module")
def grade():
    return ler(PLANILHA)


@pytest.fixture(scope="module")
def esperado():
    return json.loads((ANEXOS / "grade_20262_esperado.json").read_text("utf-8"))


def _turmas(colunas):
    return {
        (curso, ct.turno, ct.periodo_numero)
        for ct in colunas
        if ct.e_turma
        for curso in ct.cursos
    }


class TestTurmas:
    """RN-04 — a chave é (curso, turno, período). Módulo e rótulo ficam fora."""

    def test_total(self, grade, esperado):
        colunas, _ = grade
        assert len(_turmas(colunas)) == esperado["resumo"]["turmas"] == 17

    def test_colunas_mescladas_viram_uma_turma(self, grade):
        """Educação Física Matutino: colunas D e E mescladas = 1 turma."""
        colunas, _ = grade
        ef = [c for c in colunas if "Educação Física_Matutino" in c.aba]
        assert len(ef) == 1
        assert len(ef[0].colunas) == 2

    def test_sub_turmas_colapsam(self, grade):
        """Sub-Turma A e B de Biomedicina Matutino são a MESMA turma (4º)."""
        colunas, _ = grade
        bio = [c for c in colunas if c.aba == "Biomedicina- Matutino"]
        assert len(bio) == 2, "duas colunas na planilha"
        assert {c.periodo_numero for c in bio} == {4}, "mesma turma do 4º período"

    def test_periodo_ignora_instrucao_de_matricula(self, grade):
        """'Matricular 3, 4, 5 e 6 períodos' não pode virar turma do 6º."""
        colunas, _ = grade
        bio = [c for c in colunas if c.aba == "Biomedicina- Matutino"]
        assert all(c.periodo_numero == 4 for c in bio)

    def test_ciclo_basico_expande_em_cursos_reais(self, grade):
        """RN-03 — CICLO_BASICO não é curso."""
        colunas, _ = grade
        ciclo = [c for c in colunas if c.compartilhada]
        assert ciclo, "a planilha tem abas de ciclo básico"
        for c in ciclo:
            assert "CICLO" not in c.cursos
            assert c.cursos, "toda coluna compartilhada expande em cursos reais"
        matutino = next(c for c in ciclo if "Ciclo básico" in c.aba)
        assert set(matutino.cursos) == {"BIOMEDICINA", "ENFERMAGEM"}

    def test_estagio_nao_e_turma(self, grade):
        colunas, _ = grade
        nao_turma = [c for c in colunas if not c.e_turma]
        assert len(nao_turma) == 1
        assert "Estágio" in " ".join(nao_turma[0].cabecalho)


class TestOfertas:
    """RN-09 — a chave é (disciplina, professor), sem a turma."""

    def test_total(self, grade, esperado):
        _, linhas = grade
        pares = {
            (
                _canon(ln.aula.disciplina, ALIAS_DISCIPLINA),
                _canon(ln.aula.professor, ALIAS_PROFESSOR),
            )
            for ln in linhas
            if ln.aula.professor
        }
        assert len(pares) == esperado["resumo"]["ofertas"] == 105

    def test_modalidade_nao_duplica_oferta(self, grade):
        """RN-10 — 'Toxicologia - Preleção' e '- Prática' do mesmo professor
        são UMA oferta; a modalidade é atributo da alocação."""
        _, linhas = grade
        tox = [
            ln
            for ln in linhas
            if _canon(ln.aula.disciplina, ALIAS_DISCIPLINA) == "toxicologia"
            and _canon(ln.aula.professor, ALIAS_PROFESSOR) == "washington"
        ]
        assert len(tox) > 1, "aparece em mais de uma alocação"
        assert {ln.aula.disciplina for ln in tox} == {"Toxicologia"}

    def test_professores_diferentes_geram_ofertas_distintas(self, grade):
        """RN-08 — mesma disciplina, professores diferentes = ofertas distintas."""
        _, linhas = grade
        bioq = {
            _canon(ln.aula.professor, ALIAS_PROFESSOR)
            for ln in linhas
            if _canon(ln.aula.disciplina, ALIAS_DISCIPLINA) == "bioquimica"
        }
        assert len(bioq) > 1


class TestAlocacoes:
    def test_mescla_vertical_vira_uma_alocacao(self, grade, esperado):
        _, linhas = grade
        assert len(linhas) == esperado["resumo"]["alocacoes"] == 164
        assert any(ln.duracao_horarios > 1 for ln in linhas)

    def test_texto_origem_sempre_preenchido(self, grade):
        """RN-11 — rastreabilidade de 100% das alocações."""
        _, linhas = grade
        assert all(ln.aula.texto_origem for ln in linhas)

    def test_status_das_linhas(self, grade, esperado):
        _, linhas = grade
        contagem = {"OK": 0, "REVISAR": 0, "ERRO": 0}
        for ln in linhas:
            contagem[ln.aula.status.value] += 1
        assert contagem == esperado["resumo"]["linhas_por_status"]
        assert contagem["ERRO"] == 1, "o bilhete do 'Preceptor (A contratar)'"
