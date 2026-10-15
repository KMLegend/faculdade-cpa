"""Motor de Formulários (doc 04 §4, doc 05 §1 e §2).

Responsável pela montagem determinística de formulários, snapshot de perguntas,
geração em lote e ciclo de vida.
"""

from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ConflitoEstado, NaoEncontrado
from app.core.texto import slugificar
from app.models import (
    AplicacaoPergunta, BlocoPergunta, DimensaoSinaes, EixoSinaes, Formulario,
    FormularioPergunta, Oferta, OfertaTurma, PeriodoLetivo, Pergunta,
    PerguntaVinculo, SEGMENTO_DO_INSTRUMENTO, StatusFormulario, TipoAlvo,
    TipoInstrumento, Turma,
)
from app.schemas.formularios import JanelaEntrada

LIMITE_ALERTA_PERGUNTAS = 150
SEGUNDOS_POR_PERGUNTA = 5

NOMES_SEGMENTO = {
    TipoInstrumento.DOCENTE: "Docente",
    TipoInstrumento.TECNICO_ADMINISTRATIVO: "Técnico-Administrativa",
    TipoInstrumento.COMUNIDADE: "da Comunidade Externa",
}


def titulo_formulario(
    tipo: TipoInstrumento,
    periodo_codigo: str,
    turma: Turma | None = None,
) -> str:
    """Padronização de títulos conforme doc 05 §1."""
    if tipo == TipoInstrumento.DISCENTE_TURMA and turma is not None:
        return f"CPA {periodo_codigo} — {turma.rotulo}"
    nome_seg = NOMES_SEGMENTO.get(tipo, tipo.value)
    return f"CPA {periodo_codigo} — Avaliação {nome_seg}"


def vinculo_casa(
    p: Pergunta,
    oferta: Oferta,
    turma: Turma | None = None,
) -> bool:
    """Verifica se a pergunta com aplicação ESPECIFICA se aplica à oferta."""
    if p.aplicacao == AplicacaoPergunta.TODAS:
        return True

    for v in p.vinculos:
        if v.alvo_tipo == TipoAlvo.DISCIPLINA and v.alvo_id == oferta.disciplina_id:
            return True
        if v.alvo_tipo == TipoAlvo.PROFESSOR and v.alvo_id == oferta.professor_id:
            return True
        if v.alvo_tipo == TipoAlvo.CURSO:
            if oferta.disciplina and oferta.disciplina.curso_id == v.alvo_id:
                return True
            if turma and turma.curso_id == v.alvo_id:
                return True
    return False


def criar_snapshot_item(
    p: Pergunta,
    oferta: Oferta | None,
    ordem: int,
) -> FormularioPergunta:
    """Cria uma instância de FormularioPergunta congelando o estado da Pergunta (RN-26)."""
    rotulo = None
    if oferta is not None:
        prof_nome = (
            oferta.professor.nome_exibicao
            if oferta.professor
            else "Docente"
        )
        disc_nome = (
            oferta.disciplina.nome
            if oferta.disciplina
            else "Disciplina"
        )
        rotulo = f"{disc_nome} · Prof. {prof_nome}"

    return FormularioPergunta(
        pergunta_id=p.id,
        codigo=p.codigo,
        equivalencia_id=p.equivalencia_id,
        versao_texto=p.versao_texto,
        dimensao_id=p.dimensao_id,
        oferta_id=oferta.id if oferta else None,
        bloco=p.bloco,
        rotulo_oferta=rotulo,
        texto_snapshot=p.texto,
        tipo_snapshot=p.tipo,
        opcoes_snapshot=p.opcoes,
        obrigatoria_snapshot=p.obrigatoria,
        ordem=ordem,
    )


async def montar(
    formulario: Formulario,
    s: AsyncSession,
) -> list[FormularioPergunta]:
    """Algoritmo de montagem determinístico (doc 04 §4)."""
    itens: list[FormularioPergunta] = []
    ordem = 0
    ti = formulario.tipo_instrumento

    if ti == TipoInstrumento.DISCENTE_TURMA:
        # 1) Bloco institucional — 48 perguntas, uma vez
        perguntas_inst = (
            await s.scalars(
                select(Pergunta)
                .where(
                    Pergunta.tipo_instrumento == ti,
                    Pergunta.bloco == BlocoPergunta.INSTITUCIONAL,
                    Pergunta.ativo.is_(True),
                )
                .order_by(Pergunta.ordem_exibicao, Pergunta.codigo)
            )
        ).all()

        for p in perguntas_inst:
            ordem += 1
            itens.append(criar_snapshot_item(p, oferta=None, ordem=ordem))

        # 2) Bloco por matéria — 10 perguntas por oferta avaliável da turma
        turma = None
        if formulario.turma_id is not None:
            turma = await s.scalar(
                select(Turma)
                .where(Turma.id == formulario.turma_id)
                .options(
                    selectinload(Turma.ofertas_turma)
                    .selectinload(OfertaTurma.oferta)
                    .selectinload(Oferta.disciplina),
                    selectinload(Turma.ofertas_turma)
                    .selectinload(OfertaTurma.oferta)
                    .selectinload(Oferta.professor),
                    selectinload(Turma.curso),
                )
            )
            formulario.turma = turma

        ofertas_candidatas: list[Oferta] = []
        if turma is not None:
            for ot in turma.ofertas_turma:
                if ot.oferta and ot.oferta.avaliavel and ot.oferta.ativo:
                    ofertas_candidatas.append(ot.oferta)

        # Ordenação determinística RN-23
        ofertas_candidatas.sort(
            key=lambda o: (
                slugificar(o.disciplina.nome if o.disciplina else ""),
                slugificar(o.professor.nome_exibicao if o.professor else ""),
                o.id,
            )
        )

        perguntas_materia = (
            await s.scalars(
                select(Pergunta)
                .where(
                    Pergunta.tipo_instrumento == ti,
                    Pergunta.bloco.in_([BlocoPergunta.PROFESSOR, BlocoPergunta.DISCIPLINA]),
                    Pergunta.ativo.is_(True),
                )
                .options(selectinload(Pergunta.vinculos))
                .order_by(Pergunta.ordem_exibicao, Pergunta.codigo)
            )
        ).all()

        for oferta in ofertas_candidatas:
            for bloco in (BlocoPergunta.PROFESSOR, BlocoPergunta.DISCIPLINA):
                for p in perguntas_materia:
                    if p.bloco == bloco and (
                        p.aplicacao == AplicacaoPergunta.TODAS
                        or vinculo_casa(p, oferta, turma)
                    ):
                        ordem += 1
                        itens.append(criar_snapshot_item(p, oferta=oferta, ordem=ordem))

    else:
        # Instrumentos institucionais agrupados por eixo e dimensão
        perguntas_inst = (
            await s.scalars(
                select(Pergunta)
                .join(DimensaoSinaes, Pergunta.dimensao_id == DimensaoSinaes.id)
                .join(EixoSinaes, DimensaoSinaes.eixo_id == EixoSinaes.id)
                .where(
                    Pergunta.tipo_instrumento == ti,
                    Pergunta.ativo.is_(True),
                )
                .order_by(
                    EixoSinaes.numero,
                    DimensaoSinaes.numero,
                    Pergunta.ordem_exibicao,
                    Pergunta.codigo,
                )
            )
        ).all()

        for p in perguntas_inst:
            ordem += 1
            itens.append(criar_snapshot_item(p, oferta=None, ordem=ordem))

    return itens


async def gerar_lote(
    periodo_letivo_id: int,
    janelas: dict[str, JanelaEntrada] | None,
    s: AsyncSession,
) -> dict:
    """Gera em lote os formulários do período (doc 05 §1)."""
    periodo = await s.get(PeriodoLetivo, periodo_letivo_id)
    if periodo is None:
        raise NaoEncontrado(f"Período letivo {periodo_letivo_id} não encontrado.")

    criados = 0
    pulados = 0
    sem_oferta = []
    alertas = []

    # 1) DISCENTE_TURMA — uma por turma ativa
    turmas_ativas = (
        await s.scalars(
            select(Turma)
            .where(
                Turma.periodo_letivo_id == periodo.id,
                Turma.ativo.is_(True),
            )
            .options(
                selectinload(Turma.ofertas_turma)
                .selectinload(OfertaTurma.oferta)
                .selectinload(Oferta.disciplina),
                selectinload(Turma.ofertas_turma)
                .selectinload(OfertaTurma.oferta)
                .selectinload(Oferta.professor),
                selectinload(Turma.curso),
            )
        )
    ).all()

    for turma in turmas_ativas:
        ofertas = [
            ot.oferta
            for ot in turma.ofertas_turma
            if ot.oferta and ot.oferta.avaliavel and ot.oferta.ativo
        ]
        if not ofertas:
            # RN-30: Turma sem ofertas avaliáveis não gera formulário
            sem_oferta.append({
                "id": turma.id,
                "rotulo": turma.rotulo,
                "motivo": "Nenhuma oferta avaliável vinculada",
            })
            continue

        janela = (
            janelas.get(TipoInstrumento.DISCENTE_TURMA.value)
            if janelas
            else None
        )
        abre_em = janela.abre_em if janela else None
        fecha_em = janela.fecha_em if janela else None

        existente = await s.scalar(
            select(Formulario).where(
                Formulario.periodo_letivo_id == periodo.id,
                Formulario.turma_id == turma.id,
                Formulario.tipo_instrumento == TipoInstrumento.DISCENTE_TURMA,
            )
        )

        if existente is not None and existente.status != StatusFormulario.RASCUNHO:
            pulados += 1
            continue

        if existente is None:
            formulario = Formulario(
                uuid=uuid_lib.uuid4(),
                periodo_letivo_id=periodo.id,
                tipo_instrumento=TipoInstrumento.DISCENTE_TURMA,
                segmento=SEGMENTO_DO_INSTRUMENTO[TipoInstrumento.DISCENTE_TURMA],
                turma_id=turma.id,
                titulo=titulo_formulario(TipoInstrumento.DISCENTE_TURMA, periodo.codigo, turma),
                status=StatusFormulario.RASCUNHO,
                abre_em=abre_em,
                fecha_em=fecha_em,
            )
            formulario.turma = turma
            s.add(formulario)
            await s.flush()
        else:
            formulario = existente
            formulario.titulo = titulo_formulario(TipoInstrumento.DISCENTE_TURMA, periodo.codigo, turma)
            formulario.turma = turma
            if abre_em:
                formulario.abre_em = abre_em
            if fecha_em:
                formulario.fecha_em = fecha_em
            # Limpa snapshot anterior
            await s.execute(
                delete(FormularioPergunta).where(
                    FormularioPergunta.formulario_id == formulario.id
                )
            )
            await s.flush()

        itens = await montar(formulario, s)
        for item in itens:
            item.formulario_id = formulario.id
            s.add(item)
        await s.flush()

        if len(itens) > LIMITE_ALERTA_PERGUNTAS:
            alertas.append({
                "formulario_id": formulario.id,
                "titulo": formulario.titulo,
                "total_perguntas": len(itens),
                "limite": LIMITE_ALERTA_PERGUNTAS,
            })

        criados += 1

    # 2) Segmentos institucionais (DOCENTE, TECNICO_ADMINISTRATIVO, COMUNIDADE)
    for ti in (
        TipoInstrumento.DOCENTE,
        TipoInstrumento.TECNICO_ADMINISTRATIVO,
        TipoInstrumento.COMUNIDADE,
    ):
        janela = janelas.get(ti.value) if janelas else None
        abre_em = janela.abre_em if janela else None
        fecha_em = janela.fecha_em if janela else None

        existente = await s.scalar(
            select(Formulario).where(
                Formulario.periodo_letivo_id == periodo.id,
                Formulario.tipo_instrumento == ti,
            )
        )

        if existente is not None and existente.status != StatusFormulario.RASCUNHO:
            pulados += 1
            continue

        if existente is None:
            formulario = Formulario(
                uuid=uuid_lib.uuid4(),
                periodo_letivo_id=periodo.id,
                tipo_instrumento=ti,
                segmento=SEGMENTO_DO_INSTRUMENTO[ti],
                turma_id=None,
                titulo=titulo_formulario(ti, periodo.codigo),
                status=StatusFormulario.RASCUNHO,
                abre_em=abre_em,
                fecha_em=fecha_em,
            )
            s.add(formulario)
            await s.flush()
        else:
            formulario = existente
            formulario.titulo = titulo_formulario(ti, periodo.codigo)
            if abre_em:
                formulario.abre_em = abre_em
            if fecha_em:
                formulario.fecha_em = fecha_em
            await s.execute(
                delete(FormularioPergunta).where(
                    FormularioPergunta.formulario_id == formulario.id
                )
            )
            await s.flush()

        itens = await montar(formulario, s)
        for item in itens:
            item.formulario_id = formulario.id
            s.add(item)
        await s.flush()

        if len(itens) > LIMITE_ALERTA_PERGUNTAS:
            alertas.append({
                "formulario_id": formulario.id,
                "titulo": formulario.titulo,
                "total_perguntas": len(itens),
                "limite": LIMITE_ALERTA_PERGUNTAS,
            })

        criados += 1

    await s.commit()

    return {
        "criados": criados,
        "pulados": pulados,
        "sem_oferta": sem_oferta,
        "alertas": alertas,
    }


from datetime import datetime, timedelta, timezone

async def publicar_formulario(formulario_id: int, s: AsyncSession) -> Formulario:
    """Publica um formulário individualmente."""
    formulario = await s.get(
        Formulario,
        formulario_id,
        options=[selectinload(Formulario.itens)],
    )
    if formulario is None:
        raise NaoEncontrado(f"Formulário {formulario_id} não encontrado.")

    if formulario.status == StatusFormulario.PUBLICADO:
        return formulario

    if not formulario.itens:
        raise ConflitoEstado("Não é possível publicar formulário sem perguntas no snapshot.")

    agora = datetime.now(timezone.utc)
    if not formulario.abre_em:
        formulario.abre_em = agora
    if not formulario.fecha_em or formulario.fecha_em <= formulario.abre_em:
        formulario.fecha_em = formulario.abre_em + timedelta(days=15)

    formulario.status = StatusFormulario.PUBLICADO
    await s.commit()
    await s.refresh(formulario)
    return formulario


async def encerrar_formulario(formulario_id: int, s: AsyncSession) -> Formulario:
    """Encerra um formulário."""
    formulario = await s.get(Formulario, formulario_id)
    if formulario is None:
        raise NaoEncontrado(f"Formulário {formulario_id} não encontrado.")

    formulario.status = StatusFormulario.ENCERRADO
    await s.commit()
    await s.refresh(formulario)
    return formulario


async def publicar_lote(
    periodo_letivo_id: int | None,
    tipo_instrumento: TipoInstrumento | None,
    s: AsyncSession,
) -> dict:
    """Publica em lote formulários em RASCUNHO (doc 05 §2)."""
    q = select(Formulario).where(Formulario.status == StatusFormulario.RASCUNHO)
    if periodo_letivo_id:
        q = q.where(Formulario.periodo_letivo_id == periodo_letivo_id)
    if tipo_instrumento:
        q = q.where(Formulario.tipo_instrumento == tipo_instrumento)

    formularios = (await s.scalars(q.options(selectinload(Formulario.itens)))).all()
    publicados_ids = []

    agora = datetime.now(timezone.utc)
    for f in formularios:
        if not f.itens:
            continue
        if not f.abre_em:
            f.abre_em = agora
        if not f.fecha_em or f.fecha_em <= f.abre_em:
            f.fecha_em = f.abre_em + timedelta(days=15)
        f.status = StatusFormulario.PUBLICADO
        publicados_ids.append(f.id)

    await s.commit()
    return {
        "publicados": len(publicados_ids),
        "ids": publicados_ids,
    }

