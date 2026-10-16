"""Relatórios da CPA (doc 08 §3).

Duas regras atravessam todos eles:

1. **Limiar de exibição** (RN-34) — abaixo do mínimo, nada é mostrado. Em turma
   pequena, uma média baixa somada a um comentário identifica a pessoa.
2. **Agregação `pooled`** — sempre a partir das respostas individuais, nunca
   média de médias.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import obter_settings
from app.models import (
    Curso, DimensaoSinaes, Disciplina, EixoSinaes, Formulario, FormularioPergunta,
    Oferta, Professor, RespostaItem, Segmento, StatusFormulario, Submissao, Turma,
)
from app.services.isg import agregar

#: Segmentos de universo pequeno — limiar próprio (RN-34).
SEGMENTOS_RESTRITOS = {Segmento.TECNICO_ADMINISTRATIVO, Segmento.COMUNIDADE}


def limiar_de(segmento: Segmento | None) -> int:
    s = obter_settings()
    return (
        s.min_respostas_exibicao_restrito
        if segmento in SEGMENTOS_RESTRITOS
        else s.min_respostas_exibicao
    )


@dataclass
class Celula:
    """Um número do relatório — ou a razão de ele não aparecer."""

    respostas: int
    agregado: dict | None
    suprimido: bool
    motivo: str | None = None

    def como_dict(self) -> dict:
        if self.suprimido:
            return {
                "respostas": self.respostas,
                "suprimido": True,
                "motivo": self.motivo,
                "isg_pct": None,
                "media": None,
            }
        return {"suprimido": False, **(self.agregado or {})}


def _celula(
    valores: list[int | None], submissoes: int, segmento: Segmento | None
) -> Celula:
    if not valores:
        return Celula(0, None, True, "DIMENSAO_NAO_APLICADA")
    minimo = limiar_de(segmento)
    if submissoes < minimo:
        return Celula(submissoes, None, True, "AMOSTRA_INSUFICIENTE")
    return Celula(submissoes, agregar(valores).como_dict(), False)


async def _contar_submissoes(s: AsyncSession, **filtros) -> int:
    q = select(func.count(func.distinct(Submissao.id))).select_from(Submissao)
    q = q.join(Formulario, Formulario.id == Submissao.formulario_id)
    for campo, valor in filtros.items():
        q = q.where(getattr(Formulario, campo) == valor)
    return await s.scalar(q) or 0


# ─── adesão (durante a janela; só contagens) ─────────────────────────────────
async def adesao(periodo_letivo_id: int, s: AsyncSession) -> dict:
    """Único relatório visível com a avaliação aberta — nunca mostra conteúdo."""
    linhas = (
        await s.execute(
            select(
                Formulario.tipo_instrumento,
                func.count(func.distinct(Formulario.id)),
                func.count(func.distinct(Submissao.id)),
            )
            .outerjoin(Submissao, Submissao.formulario_id == Formulario.id)
            .where(Formulario.periodo_letivo_id == periodo_letivo_id)
            .group_by(Formulario.tipo_instrumento)
        )
    ).all()

    sem_resposta = (
        await s.scalars(
            select(Formulario.titulo)
            .outerjoin(Submissao, Submissao.formulario_id == Formulario.id)
            .where(
                Formulario.periodo_letivo_id == periodo_letivo_id,
                Formulario.status == StatusFormulario.PUBLICADO,
                Submissao.id.is_(None),
            )
        )
    ).all()

    return {
        "periodo_letivo_id": periodo_letivo_id,
        "instrumentos": [
            {
                "tipo_instrumento": tipo.value,
                "formularios": formularios,
                "submissoes": submissoes,
            }
            for tipo, formularios, submissoes in linhas
        ],
        # Acionável: a aplicação não aconteceu e a CPA precisa cobrar.
        "publicados_sem_resposta": list(sem_resposta),
    }


# ─── por dimensão × segmento (o que o MEC pede) ──────────────────────────────
async def por_dimensao(
    periodo_letivo_id: int, s: AsyncSession, segmento: Segmento | None = None
) -> dict:
    eixos = {
        e.id: e for e in (await s.scalars(select(EixoSinaes).order_by(EixoSinaes.numero))).all()
    }
    dimensoes = (
        await s.scalars(select(DimensaoSinaes).order_by(DimensaoSinaes.numero))
    ).all()

    q = (
        select(
            FormularioPergunta.dimensao_id,
            Formulario.segmento,
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
    if segmento:
        q = q.where(Formulario.segmento == segmento)

    bruto: dict[tuple[int, Segmento], list[int]] = {}
    submissoes: dict[tuple[int, Segmento], set[int]] = {}
    for dim_id, seg, valor, sub_id in (await s.execute(q)).all():
        bruto.setdefault((dim_id, seg), []).append(valor)
        submissoes.setdefault((dim_id, seg), set()).add(sub_id)

    segmentos = [segmento] if segmento else list(Segmento)
    saida_eixos: list[dict] = []
    for eixo in sorted(eixos.values(), key=lambda e: e.numero):
        dims_do_eixo = [d for d in dimensoes if d.eixo_id == eixo.id]
        if not dims_do_eixo:
            continue
        saida_eixos.append(
            {
                "numero": eixo.numero,
                "nome": eixo.nome,
                "dimensoes": [
                    {
                        "numero": d.numero,
                        "nome": d.nome,
                        # Emite os DOIS rótulos: a série histórica do painel
                        # continua comparável (doc 02).
                        "nome_institucional": d.nome_institucional,
                        "por_segmento": {
                            seg.value: _celula(
                                bruto.get((d.id, seg), []),
                                len(submissoes.get((d.id, seg), set())),
                                seg,
                            ).como_dict()
                            for seg in segmentos
                        },
                        "geral": _celula(
                            [v for seg in segmentos for v in bruto.get((d.id, seg), [])],
                            len(
                                {
                                    x
                                    for seg in segmentos
                                    for x in submissoes.get((d.id, seg), set())
                                }
                            ),
                            None,
                        ).como_dict(),
                    }
                    for d in dims_do_eixo
                ],
            }
        )
    return {"periodo_letivo_id": periodo_letivo_id, "eixos": saida_eixos}


# ─── por questão (reproduz a página "ISG por Questão" do painel) ─────────────
async def por_questao(periodo_letivo_id: int, s: AsyncSession) -> list[dict]:
    linhas = (
        await s.execute(
            select(
                FormularioPergunta.codigo,
                FormularioPergunta.equivalencia_id,
                FormularioPergunta.texto_snapshot,
                FormularioPergunta.dimensao_id,
                Formulario.segmento,
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

    por_codigo: dict[int, dict] = {}
    for codigo, equiv, texto, dim, seg, valor, sub in linhas:
        reg = por_codigo.setdefault(
            codigo,
            {
                "codigo": codigo,
                "equivalencia_id": equiv,
                "texto": texto,
                "dimensao": dim,
                "segmento": seg.value,
                "_valores": [],
                "_subs": set(),
            },
        )
        reg["_valores"].append(valor)
        reg["_subs"].add(sub)

    saida = []
    for reg in por_codigo.values():
        celula = _celula(
            reg["_valores"], len(reg["_subs"]), Segmento(reg["segmento"])
        )
        saida.append(
            {
                k: v for k, v in reg.items() if not k.startswith("_")
            } | celula.como_dict()
        )
    return sorted(saida, key=lambda r: (r.get("isg_pct") is None, -(r.get("isg_pct") or 0)))


# ─── por oferta / professor ──────────────────────────────────────────────────
async def por_oferta(oferta_id: int, s: AsyncSession) -> dict:
    oferta = await s.get(Oferta, oferta_id)
    if oferta is None:
        return {"oferta_id": oferta_id, "encontrada": False}

    linhas = (
        await s.execute(
            select(
                FormularioPergunta.codigo,
                FormularioPergunta.texto_snapshot,
                FormularioPergunta.bloco,
                RespostaItem.valor_numerico,
                RespostaItem.valor_texto,
                RespostaItem.oculto,
                Submissao.id,
                Formulario.status,
            )
            .select_from(RespostaItem)
            .join(Submissao, Submissao.id == RespostaItem.submissao_id)
            .join(Formulario, Formulario.id == Submissao.formulario_id)
            .join(
                FormularioPergunta,
                FormularioPergunta.id == RespostaItem.formulario_pergunta_id,
            )
            .where(FormularioPergunta.oferta_id == oferta_id)
        )
    ).all()

    submissoes = {l[6] for l in linhas}
    limiar = obter_settings().min_respostas_exibicao
    disciplina = await s.get(Disciplina, oferta.disciplina_id)
    professor = await s.get(Professor, oferta.professor_id)
    cabecalho = {
        "oferta_id": oferta_id,
        "disciplina": disciplina.nome if disciplina else None,
        "professor": professor.nome_exibicao if professor else None,
        "submissoes": len(submissoes),
    }

    if len(submissoes) < limiar:
        return {
            **cabecalho,
            "suprimido": True,
            "motivo": "AMOSTRA_INSUFICIENTE",
            "limiar": limiar,
            "perguntas": [],
            "comentarios": [],
        }

    por_codigo: dict[int, dict] = {}
    comentarios: list[dict] = []
    encerrado = all(l[7] == StatusFormulario.ENCERRADO for l in linhas)

    for codigo, texto, bloco, numerico, livre, oculto, _sub, _st in linhas:
        if livre:
            # RN-35 — comentário só aparece depois do encerramento.
            if encerrado and not oculto:
                comentarios.append({"codigo": codigo, "texto": livre})
            continue
        reg = por_codigo.setdefault(
            codigo,
            {"codigo": codigo, "texto": texto, "bloco": bloco.value, "_valores": []},
        )
        reg["_valores"].append(numerico)

    return {
        **cabecalho,
        "suprimido": False,
        "perguntas": [
            {k: v for k, v in r.items() if not k.startswith("_")}
            | agregar(r["_valores"]).como_dict()
            for r in por_codigo.values()
        ],
        "comentarios": comentarios,
        "comentarios_liberados": encerrado,
    }


async def por_professor(
    professor_id: int, periodo_letivo_id: int, s: AsyncSession
) -> dict:
    professor = await s.get(Professor, professor_id)
    if professor is None:
        return {"professor_id": professor_id, "encontrado": False}

    ofertas = (
        await s.scalars(
            select(Oferta).where(
                Oferta.professor_id == professor_id,
                Oferta.periodo_letivo_id == periodo_letivo_id,
            )
        )
    ).all()

    detalhes, suprimidas, valores = [], 0, []
    for oferta in ofertas:
        r = await por_oferta(oferta.id, s)
        if r.get("suprimido"):
            suprimidas += 1
            continue
        detalhes.append(r)
        valores += [
            v
            for p in r["perguntas"]
            for v in [p["media"]] * p["respostas"]
            if p["media"] is not None
        ]

    return {
        "professor_id": professor_id,
        "professor": professor.nome_exibicao,
        "ofertas_avaliadas": len(detalhes),
        # Informar quantas saíram evita mascarar viés de seleção.
        "ofertas_suprimidas": suprimidas,
        "ofertas": detalhes,
    }
