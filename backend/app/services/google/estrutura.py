"""Estrutura desejada → itens da Forms API (doc 10 §3).

A decisão central: cada bloco vira uma **grade** (`questionGroupItem`), não N
perguntas soltas. Um formulário de 167 perguntas passa de 167 campos para ~20
blocos visuais — é a diferença entre viável e inviável no celular.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from app.models import BlocoPergunta, FormularioPergunta, TipoPergunta

#: Rótulos da escala. As pontas nomeadas bastam: nomear os cinco polui a grade.
COLUNAS_LIKERT = ["1", "2", "3", "4", "5"]
LEGENDA_LIKERT = "1 = Discordo totalmente · 5 = Concordo totalmente"


@dataclass
class Bloco:
    """Um agrupamento que vira uma página + uma grade no Google."""

    titulo: str
    descricao: str | None
    perguntas: list[FormularioPergunta]
    #: NULL no bloco institucional; preenchido no bloco de matéria.
    oferta_id: int | None = None
    dimensao: int | None = None


@dataclass
class EstruturaDesejada:
    titulo: str
    descricao: str
    blocos: list[Bloco] = field(default_factory=list)
    #: Perguntas de texto livre vão soltas no fim: não cabem em grade.
    texto_livre: list[FormularioPergunta] = field(default_factory=list)

    @property
    def total_perguntas(self) -> int:
        return sum(len(b.perguntas) for b in self.blocos) + len(self.texto_livre)

    def hash(self) -> str:
        """Impressão digital da estrutura (doc 10 §6.2).

        Igual ⇒ a sincronização não emite nenhuma request. Cobre o que muda o
        formulário: ordem, texto, tipo e rótulo da oferta.
        """
        corpo = {
            "titulo": self.titulo,
            "blocos": [
                {
                    "titulo": b.titulo,
                    "oferta_id": b.oferta_id,
                    "perguntas": [
                        [p.codigo, p.versao_texto, p.texto_snapshot, p.tipo_snapshot.value]
                        for p in b.perguntas
                    ],
                }
                for b in self.blocos
            ],
            "texto_livre": [
                [p.codigo, p.versao_texto, p.texto_snapshot] for p in self.texto_livre
            ],
        }
        bruto = json.dumps(corpo, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def agrupar(
    titulo: str, itens: list[FormularioPergunta], dimensoes: dict[int, str]
) -> EstruturaDesejada:
    """Organiza o snapshot em blocos: institucional por dimensão, matéria por oferta."""
    estrutura = EstruturaDesejada(
        titulo=titulo,
        descricao=(
            "Sua resposta é ANÔNIMA. Não há login e nenhum dado pessoal seu é "
            "registrado. Leva poucos minutos."
        ),
    )

    institucionais: dict[int, list[FormularioPergunta]] = {}
    materias: dict[int, list[FormularioPergunta]] = {}

    for item in sorted(itens, key=lambda i: i.ordem):
        if item.tipo_snapshot is TipoPergunta.TEXTO_LIVRE:
            estrutura.texto_livre.append(item)
        elif item.bloco is BlocoPergunta.INSTITUCIONAL:
            institucionais.setdefault(item.dimensao_id, []).append(item)
        else:
            materias.setdefault(item.oferta_id, []).append(item)

    for dimensao_id, perguntas in institucionais.items():
        estrutura.blocos.append(
            Bloco(
                titulo=dimensoes.get(dimensao_id, "Avaliação institucional"),
                descricao=LEGENDA_LIKERT,
                perguntas=perguntas,
                dimensao=dimensao_id,
            )
        )

    for oferta_id, perguntas in materias.items():
        estrutura.blocos.append(
            Bloco(
                titulo=perguntas[0].rotulo_oferta or "Disciplina",
                descricao=LEGENDA_LIKERT,
                perguntas=perguntas,
                oferta_id=oferta_id,
            )
        )
    return estrutura


def para_requests(estrutura: EstruturaDesejada) -> list[dict]:
    """Converte a estrutura em requests de `batchUpdate`, na ordem final."""
    requests: list[dict] = [
        {
            "updateFormInfo": {
                "info": {
                    "title": estrutura.titulo,
                    "description": estrutura.descricao,
                },
                "updateMask": "title,description",
            }
        },
        # Anonimato afirmado junto com a estrutura (doc 10 §5).
        {
            "updateSettings": {
                "settings": {"emailCollectionType": "DO_NOT_COLLECT"},
                "updateMask": "emailCollectionType",
            }
        },
    ]

    indice = 0
    for bloco in estrutura.blocos:
        requests.append(
            {
                "createItem": {
                    "item": {
                        "title": bloco.titulo,
                        "pageBreakItem": {},
                    },
                    "location": {"index": indice},
                }
            }
        )
        indice += 1
        requests.append(
            {
                "createItem": {
                    "item": {
                        "title": bloco.titulo,
                        "description": bloco.descricao,
                        "questionGroupItem": _grade(bloco.perguntas),
                    },
                    "location": {"index": indice},
                }
            }
        )
        indice += 1

    for pergunta in estrutura.texto_livre:
        requests.append(
            {
                "createItem": {
                    "item": {
                        "title": pergunta.texto_snapshot,
                        "questionItem": {
                            "question": {
                                "required": False,  # RN-21
                                "textQuestion": {"paragraph": True},
                            }
                        },
                    },
                    "location": {"index": indice},
                }
            }
        )
        indice += 1

    return requests


def _grade(perguntas: list[FormularioPergunta]) -> dict:
    """Um `questionGroupItem`: linhas = perguntas, colunas = escala 1–5."""
    return {
        "questions": [
            {
                "required": p.obrigatoria_snapshot,
                "rowQuestion": {"title": p.texto_snapshot},
            }
            for p in perguntas
        ],
        "grid": {
            "columns": {
                "type": "RADIO",
                "options": [{"value": v} for v in COLUNAS_LIKERT],
            },
            # Uma resposta por linha; sem isto o aluno poderia marcar a mesma
            # coluna para tudo sem perceber que faltou responder.
            "shuffleQuestions": False,
        },
    }


def mapear_question_ids(
    estrutura: EstruturaDesejada, formulario_google: dict
) -> dict[int, tuple[str, str]]:
    """Casa cada `formulario_pergunta` ao `questionId` que o Google devolveu.

    Casamento por POSIÇÃO: `montar()` é determinístico e as requests saem na
    mesma ordem, então a n-ésima linha da n-ésima grade corresponde à n-ésima
    pergunta do bloco. Nunca por texto (doc 10 §6.1.2).

    Devolve {formulario_pergunta.id: (item_id, question_id)}.
    """
    mapa: dict[int, tuple[str, str]] = {}
    grades = [
        item
        for item in formulario_google.get("items", [])
        if "questionGroupItem" in item
    ]
    soltas = [
        item for item in formulario_google.get("items", []) if "questionItem" in item
    ]

    for bloco, grade in zip(estrutura.blocos, grades, strict=False):
        item_id = grade.get("itemId", "")
        questoes = grade["questionGroupItem"].get("questions", [])
        for pergunta, questao in zip(bloco.perguntas, questoes, strict=False):
            mapa[pergunta.id] = (item_id, questao.get("questionId", ""))

    for pergunta, item in zip(estrutura.texto_livre, soltas, strict=False):
        mapa[pergunta.id] = (
            item.get("itemId", ""),
            item["questionItem"]["question"].get("questionId", ""),
        )
    return mapa
