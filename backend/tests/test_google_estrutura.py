"""Conversão da estrutura em itens da Forms API (doc 10 §3).

Inspeção pura: sem banco, sem rede, sem event loop. É o teste que trava a
decisão de usar grades em vez de perguntas soltas.
"""

from types import SimpleNamespace

from app.models import BlocoPergunta, TipoPergunta
from app.services.google.estrutura import agrupar, para_requests
from app.services.google.sincronizador import _remover_itens


class TestEstrutura:
    def test_likert_vira_grade_unica(self):
        """Três perguntas Likert = UMA grade, não três campos (doc 10 §3.1)."""
        itens = [
            SimpleNamespace(
                id=i, ordem=i, codigo=i, versao_texto=1, dimensao_id=1, oferta_id=None,
                bloco=BlocoPergunta.INSTITUCIONAL, rotulo_oferta=None,
                texto_snapshot=f"P{i}", tipo_snapshot=TipoPergunta.LIKERT_5,
                obrigatoria_snapshot=True,
            )
            for i in (1, 2, 3)
        ]
        estrutura = agrupar("t", itens, {1: "Dimensão 1"})
        assert len(estrutura.blocos) == 1
        assert len(estrutura.blocos[0].perguntas) == 3

        requests = para_requests(estrutura)
        grades = [r for r in requests if "questionGroupItem" in str(r)]
        assert len(grades) == 1, "as três viram uma grade"
        quebras = [r for r in requests if "pageBreakItem" in str(r)]
        assert len(quebras) == 1, "uma página por bloco"

    def test_hash_muda_com_o_texto(self):
        def fazer(texto):
            item = SimpleNamespace(
                id=1, ordem=1, codigo=1, versao_texto=1, dimensao_id=1, oferta_id=None,
                bloco=BlocoPergunta.INSTITUCIONAL, rotulo_oferta=None,
                texto_snapshot=texto, tipo_snapshot=TipoPergunta.LIKERT_5,
                obrigatoria_snapshot=True,
            )
            return agrupar("t", [item], {1: "D"}).hash()

        assert fazer("A") != fazer("B")
        assert fazer("A") == fazer("A")

    def test_delete_de_tras_para_frente(self):
        """Índices deslizam: apagar de frente removeria o item errado."""
        indices = [
            r["deleteItem"]["location"]["index"]
            for r in _remover_itens({"items": [{}, {}, {}]})
        ]
        assert indices == [2, 1, 0]


