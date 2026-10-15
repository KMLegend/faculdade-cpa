"""Geração de artefatos de impressão em PDF (doc 05 §4).

1. Folha da turma (A4, uma por turma)
2. Cartaz por segmento (A4, docente / técnico / comunidade)
3. Lista de conferência da turma (A4, matérias da turma vindas da grade)
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Sequence

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)

from app.models import Formulario, FormularioPergunta, OfertaTurma, TipoInstrumento, Turma
from app.services.formularios import SEGUNDOS_POR_PERGUNTA


def _gerar_imagem_qr_flowable(url: str, tamanho_cm: float = 5.5) -> Image:
    """Gera o objeto Flowable de imagem do QR Code para o ReportLab."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img_pil = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img_pil.save(buf, format="PNG")
    buf.seek(0)

    dim = tamanho_cm * cm
    return Image(buf, width=dim, height=dim)


def gerar_folha_pdf(formulario: Formulario) -> bytes:
    """Gera a folha A4 individual do formulário (turma ou segmento)."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
    )

    elementos = []
    _montar_elementos_folha(formulario, elementos)
    doc.build(elementos)
    return buf.getvalue()


def gerar_folhas_lote_pdf(formularios: Sequence[Formulario]) -> bytes:
    """Gera um PDF único contendo as folhas de vários formulários (uma por página)."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
    )

    elementos = []
    for i, form in enumerate(formularios):
        if i > 0:
            elementos.append(PageBreak())
        _montar_elementos_folha(form, elementos)

    doc.build(elementos)
    return buf.getvalue()


def _montar_elementos_folha(formulario: Formulario, elementos: list) -> None:
    """Monta os blocos da folha de aplicação conforme doc 05 §4.1 e §4.3."""
    styles = getSampleStyleSheet()

    estilo_topo = ParagraphStyle(
        "Topo",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=14,
        textColor=colors.HexColor("#64748b"),
        alignment=1,  # Centralizado
    )

    estilo_titulo = ParagraphStyle(
        "Titulo",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        alignment=1,
    )

    estilo_sub = ParagraphStyle(
        "Sub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#334155"),
        alignment=1,
    )

    estilo_url = ParagraphStyle(
        "URL",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#2563eb"),
        alignment=1,
    )

    estilo_destaque = ParagraphStyle(
        "Destaque",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0f172a"),
        alignment=1,
    )

    estilo_tempo = ParagraphStyle(
        "Tempo",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#64748b"),
        alignment=1,
    )

    estilo_rodape = ParagraphStyle(
        "Rodape",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
        alignment=1,
    )

    periodo_cod = (
        formulario.periodo_letivo.codigo
        if hasattr(formulario, "periodo_letivo") and formulario.periodo_letivo
        else "2026.2"
    )

    elementos.append(Spacer(1, 0.5 * cm))
    elementos.append(Paragraph(f"AVALIAÇÃO CPA {periodo_cod}", estilo_topo))
    elementos.append(Spacer(1, 0.3 * cm))

    total_perguntas = len(formulario.itens)
    tempo_min = max(1, round((total_perguntas * SEGUNDOS_POR_PERGUNTA) / 60))

    if formulario.tipo_instrumento == TipoInstrumento.DISCENTE_TURMA and formulario.turma:
        t = formulario.turma
        curso_nome = t.curso.nome if t.curso else "Curso"
        turno_nome = t.turno.value.title()
        periodo_rotulo = f"{t.periodo_numero}º período"
        modulo_rotulo = f" — Módulo {t.modulo}" if t.modulo else ""

        elementos.append(Paragraph(f"{curso_nome} · {turno_nome}", estilo_titulo))
        elementos.append(Spacer(1, 0.2 * cm))
        elementos.append(Paragraph(f"{periodo_rotulo}{modulo_rotulo}", estilo_sub))

        # Contagem de ofertas distintas avaliadas no formulário
        ofertas_ids = {
            item.oferta_id for item in formulario.itens if item.oferta_id is not None
        }
        qtd_ofertas = len(ofertas_ids)

        destaque_texto = f"{qtd_ofertas} matérias avaliadas · {total_perguntas} perguntas"
        tempo_texto = f"cerca de {tempo_min} minutos"
    else:
        elementos.append(Paragraph(formulario.titulo, estilo_titulo))
        elementos.append(Spacer(1, 0.2 * cm))
        elementos.append(Paragraph("Instrumento de Autoavaliação Institucional", estilo_sub))

        destaque_texto = f"{total_perguntas} perguntas"
        tempo_texto = f"cerca de {tempo_min} minutos"

    elementos.append(Spacer(1, 1.0 * cm))

    # QR Code (tamanho >= 5cm)
    url_alvo = (
        formulario.google_responder_uri
        or f"https://docs.google.com/forms/d/e/{formulario.uuid}/viewform"
    )
    qr_img = _gerar_imagem_qr_flowable(url_alvo, tamanho_cm=5.5)
    elementos.append(qr_img)
    elementos.append(Spacer(1, 0.6 * cm))

    elementos.append(Paragraph(url_alvo, estilo_url))
    elementos.append(Spacer(1, 0.8 * cm))

    elementos.append(Paragraph(destaque_texto, estilo_destaque))
    elementos.append(Spacer(1, 0.2 * cm))
    elementos.append(Paragraph(tempo_texto, estilo_tempo))

    elementos.append(Spacer(1, 1.2 * cm))
    elementos.append(
        HRFlowable(
            width="80%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=15
        )
    )

    data_inicio = (
        formulario.abre_em.strftime("%d/%m/%Y")
        if formulario.abre_em
        else "01/10/2026"
    )
    data_fim = (
        formulario.fecha_em.strftime("%d/%m/%Y")
        if formulario.fecha_em
        else "15/10/2026"
    )

    elementos.append(
        Paragraph(
            "<b>Resposta ANÔNIMA.</b> Sem login, nenhum dado pessoal seu é registrado.<br/>"
            f"Período de aplicação: {data_inicio} a {data_fim}",
            estilo_rodape,
        )
    )


def gerar_conferencia_turma_pdf(
    turma: Turma,
    periodo_codigo: str = "2026.2",
) -> bytes:
    """Gera a lista de conferência da turma (A4, doc 05 §4.2)."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
    )

    styles = getSampleStyleSheet()

    estilo_topo = ParagraphStyle(
        "ConfTopo",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.HexColor("#64748b"),
    )
    estilo_titulo = ParagraphStyle(
        "ConfTitulo",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#0f172a"),
    )
    estilo_sub = ParagraphStyle(
        "ConfSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
    )
    estilo_tabela_cab = ParagraphStyle(
        "ConfTabCab",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=colors.white,
    )
    estilo_tabela_cel = ParagraphStyle(
        "ConfTabCel",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
    )

    elementos = []
    elementos.append(Paragraph(f"CPA {periodo_codigo} — CONFERÊNCIA DE MATÉRIAS", estilo_topo))
    elementos.append(Spacer(1, 0.2 * cm))

    curso_nome = turma.curso.nome if turma.curso else "Curso"
    turno_nome = turma.turno.value.title()
    rotulo_turma = f"{curso_nome} · {turno_nome} · {turma.periodo_numero}º período"
    if turma.modulo:
        rotulo_turma += f" (Módulo {turma.modulo})"

    elementos.append(Paragraph(rotulo_turma, estilo_titulo))
    elementos.append(Spacer(1, 0.2 * cm))
    elementos.append(
        Paragraph(
            "Verificação das matérias que os discentes avaliarão nesta turma. "
            "Confira os nomes dos docentes e disciplinas antes da aplicação em sala.",
            estilo_sub,
        )
    )
    elementos.append(Spacer(1, 0.5 * cm))

    # Tabela com matérias
    linhas_tabela = [
        [
            Paragraph("Disciplina", estilo_tabela_cab),
            Paragraph("Professor(a)", estilo_tabela_cab),
            Paragraph("Avaliável", estilo_tabela_cab),
            Paragraph("Visto CPA", estilo_tabela_cab),
        ]
    ]

    ofertas_turma = sorted(
        turma.ofertas_turma,
        key=lambda ot: (
            ot.oferta.disciplina.nome if ot.oferta and ot.oferta.disciplina else "",
            ot.oferta.professor.nome_exibicao if ot.oferta and ot.oferta.professor else "",
        ),
    )

    for ot in ofertas_turma:
        o = ot.oferta
        if not o or not o.ativo:
            continue
        disc = o.disciplina.nome if o.disciplina else "—"
        prof = o.professor.nome_exibicao if o.professor else "—"
        avaliavel_txt = "Sim" if o.avaliavel else "Não"

        linhas_tabela.append([
            Paragraph(disc, estilo_tabela_cel),
            Paragraph(prof, estilo_tabela_cel),
            Paragraph(avaliavel_txt, estilo_tabela_cel),
            Paragraph("[   ] OK", estilo_tabela_cel),
        ])

    tabela = Table(
        linhas_tabela,
        colWidths=[7.0 * cm, 5.5 * cm, 2.3 * cm, 2.5 * cm],
    )
    tabela.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ])
    )
    elementos.append(tabela)

    elementos.append(Spacer(1, 1.0 * cm))
    elementos.append(
        Paragraph(
            "Responsável pela conferência: _____________________________________   Data: ____/____/2026",
            estilo_sub,
        )
    )

    doc.build(elementos)
    return buf.getvalue()
