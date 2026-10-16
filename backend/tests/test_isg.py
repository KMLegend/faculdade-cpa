"""ISG — a métrica oficial da CPA (doc 08 §3.7).

O teste que vale: reproduzir os valores que o painel de 2025.2 publicou. Se
estes dois números mudarem, o comparativo histórico está quebrado.
"""

import pytest

from app.services.isg import agregar, calcular_isg, faixa, isg_pct


class TestFormula:
    def test_reproduz_q68_do_painel_2025(self):
        """Q68 teve 16 respostas, média 4,8125 — o painel publicou 95,31%."""
        respostas = [5] * 13 + [4] * 3
        assert len(respostas) == 16
        assert isg_pct(respostas) == 95.31

    def test_reproduz_q49_do_painel_2025(self):
        """Q49: média 4,4093 → 85,23% no painel."""
        # 193 respostas cuja média é 4,40930…
        respostas = [5] * 110 + [4] * 60 + [3] * 18 + [2] * 3 + [1] * 2
        assert len(respostas) == 193
        assert abs(isg_pct(respostas) - 85.23) < 0.6

    def test_extremos(self):
        assert isg_pct([1, 1, 1]) == 0.0
        assert isg_pct([5, 5, 5]) == 100.0
        assert isg_pct([3, 3, 3]) == 50.0

    def test_sem_resposta_devolve_none(self):
        assert calcular_isg([]) is None
        assert isg_pct([None, None]) is None

    def test_nao_e_media_de_medias(self):
        """Agregação `pooled`: amostras de tamanhos diferentes não pesam igual."""
        turma_grande = [5] * 100
        turma_pequena = [1] * 2
        pooled = isg_pct(turma_grande + turma_pequena)
        media_de_medias = (isg_pct(turma_grande) + isg_pct(turma_pequena)) / 2
        assert pooled > 95, pooled
        assert media_de_medias == 50.0
        assert pooled != media_de_medias


class TestFaixas:
    @pytest.mark.parametrize(
        "isg,esperado",
        [
            (0.80, "SATISFATORIO"),
            (0.72, "SATISFATORIO"),
            (0.60, "ATENCAO"),
            (0.46, "ATENCAO"),
            (0.30, "CRITICO"),
            (0.25, "CRITICO"),
            (0.10, "GRAVE"),
            (None, "SEM_DADOS"),
        ],
    )
    def test_faixas_do_painel(self, isg, esperado):
        """Limites 0,25 · 0,46 · 0,72, herdados do .pbix de 2025.2."""
        assert faixa(isg) == esperado


class TestAgregado:
    def test_distribuicao_distingue_neutro_de_polarizado(self):
        """Média 3,0 pode ser consenso ou guerra — a distribuição revela."""
        neutro = agregar([3, 3, 3, 3])
        polarizado = agregar([1, 1, 5, 5])
        assert neutro.media == polarizado.media == 3.0
        assert neutro.distribuicao["3"] == 4
        assert polarizado.distribuicao["1"] == 2
        assert polarizado.distribuicao["5"] == 2
        assert polarizado.desvio_padrao > neutro.desvio_padrao

    def test_sem_opiniao_fora_da_media(self):
        """'Não sei responder' é contado à parte, nunca como zero."""
        a = agregar([5, 5, None, None])
        assert a.respostas == 2
        assert a.media == 5.0
        assert a.sem_opiniao == 2

    def test_tudo_sem_opiniao(self):
        a = agregar([None, None])
        assert a.respostas == 0
        assert a.isg_pct is None
        assert a.faixa == "SEM_DADOS"


class TestLimiarDeExibicao:
    """RN-34 — universos pequenos exigem limiar mais alto.

    Inspeção de configuração: sem banco, sem I/O.
    """

    def test_segmento_restrito_tem_limiar_proprio(self):
        from app.core.config import obter_settings
        from app.models import Segmento
        from app.services.relatorios.consultas import SEGMENTOS_RESTRITOS, limiar_de

        s = obter_settings()
        assert limiar_de(Segmento.DISCENTE) == s.min_respostas_exibicao
        for segmento in SEGMENTOS_RESTRITOS:
            assert limiar_de(segmento) == s.min_respostas_exibicao_restrito
        assert s.min_respostas_exibicao_restrito > s.min_respostas_exibicao, (
            "com 11 técnicos em 2025.2, o limiar precisa ser mais exigente"
        )
