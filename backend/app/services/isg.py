"""ISG — Índice de Satisfação Geral (doc 08 §3.7).

Métrica oficial da CPA desde 2025.2. Deduzida empiricamente comparando o
`consolidado_cpa.xlsx` com os valores publicados no Power BI: duas
correspondências exatas, Q68 → 95,31% e Q49 → 85,23%.

    ISG = (média das respostas − 1) / 4

⚠️ Agregue sempre a partir das RESPOSTAS individuais (`pooled`), nunca fazendo
média de ISGs já calculados: médias de médias distorcem quando as amostras têm
tamanhos diferentes — e com 4 a 12 matérias por turma elas têm.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from app.core.config import obter_settings

#: Escala Likert do instrumento: 1 a 5.
MINIMO, MAXIMO = 1, 5


def calcular_isg(valores: list[int]) -> float | None:
    """Normaliza a escala 1–5 para 0..1. `None` quando não há resposta."""
    limpos = [v for v in valores if v is not None]
    if not limpos:
        return None
    return (statistics.mean(limpos) - MINIMO) / (MAXIMO - MINIMO)


def isg_pct(valores: list[int]) -> float | None:
    """ISG em percentual, com 2 casas — o formato do painel histórico."""
    bruto = calcular_isg(valores)
    return None if bruto is None else round(bruto * 100, 2)


def faixa(isg: float | None) -> str:
    """Faixa de cor herdada do painel 2025.2 (0,25 · 0,46 · 0,72)."""
    if isg is None:
        return "SEM_DADOS"
    limites = obter_settings().faixas_isg
    if isg >= limites[2]:
        return "SATISFATORIO"
    if isg >= limites[1]:
        return "ATENCAO"
    if isg >= limites[0]:
        return "CRITICO"
    return "GRAVE"


@dataclass
class Agregado:
    """Resumo estatístico de um conjunto de respostas."""

    respostas: int
    media: float | None
    mediana: float | None
    desvio_padrao: float | None
    isg_pct: float | None
    faixa: str
    distribuicao: dict[str, int]
    #: "Não sei responder" — fora da média, contado à parte.
    sem_opiniao: int = 0

    def como_dict(self) -> dict:
        return {
            "respostas": self.respostas,
            "media": self.media,
            "mediana": self.mediana,
            "desvio_padrao": self.desvio_padrao,
            "isg_pct": self.isg_pct,
            "faixa": self.faixa,
            "distribuicao": self.distribuicao,
            "sem_opiniao": self.sem_opiniao,
        }


def agregar(valores: list[int | None]) -> Agregado:
    """Estatísticas de um conjunto de respostas numéricas.

    A DISTRIBUIÇÃO é tão importante quanto a média: média 3,0 pode ser "todo
    mundo neutro" ou "metade ama, metade odeia" — situações opostas para a
    coordenação.
    """
    validos = [v for v in valores if v is not None]
    sem_opiniao = len(valores) - len(validos)
    distribuicao = {str(n): sum(1 for v in validos if v == n) for n in range(1, 6)}

    if not validos:
        return Agregado(0, None, None, None, None, "SEM_DADOS", distribuicao, sem_opiniao)

    return Agregado(
        respostas=len(validos),
        media=round(statistics.mean(validos), 2),
        mediana=statistics.median(validos),
        desvio_padrao=(
            round(statistics.stdev(validos), 2) if len(validos) > 1 else 0.0
        ),
        isg_pct=isg_pct(validos),
        faixa=faixa(calcular_isg(validos)),
        distribuicao=distribuicao,
        sem_opiniao=sem_opiniao,
    )
