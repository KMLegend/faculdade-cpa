#!/usr/bin/env python3
"""Gera relatórios executivos em PDF sobre estimativas de desenvolvimento do Projeto CPA.

Gera 2 documentos:
1. relatorio_estimativa_financeira_cpa.pdf (Horas, taxas, custos por fase, modelos de contratação)
2. relatorio_estimativa_tempo_cpa.pdf (Apenas horas, tópicos, complexidade, cronograma e aceite técnico)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class NumberedCanvas(canvas.Canvas):
    """Canvas com numeração dinâmica de páginas (Página X de Y) e cabeçalho de continuidade."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self._doc_title = getattr(self, "_doc_title", "Projeto CPA")

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Cabeçalho a partir da página 2
        if self._pageNumber > 1:
            self.drawString(36, 842 - 28, self._doc_title)
            self.drawRightString(595 - 36, 842 - 28, "Confidencial • Uso Institucional")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(36, 842 - 32, 595 - 36, 842 - 32)

        # Rodapé em todas as páginas
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(36, 34, 595 - 36, 34)

        data_str = datetime.now().strftime("%d/%m/%Y")
        self.drawString(36, 22, f"Projeto CPA — Comissão Própria de Avaliação | Emitido em: {data_str}")
        self.drawRightString(595 - 36, 22, f"Página {self._pageNumber} de {page_count}")
        self.restoreState()


def get_styles():
    """Retorna estilos tipográficos customizados para os relatórios."""
    styles = getSampleStyleSheet()

    custom_styles = {
        "DocTitle": ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0f172a"),
        ),
        "DocSubtitle": ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#2563eb"),
        ),
        "MetaLabel": ParagraphStyle(
            "MetaLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#475569"),
        ),
        "MetaValue": ParagraphStyle(
            "MetaValue",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0f172a"),
        ),
        "SectionHeading": ParagraphStyle(
            "SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#0f2942"),
            spaceBefore=10,
            spaceAfter=4,
        ),
        "SubsectionHeading": ParagraphStyle(
            "SubsectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#1e40af"),
            spaceBefore=6,
            spaceAfter=2,
        ),
        "BodyDark": ParagraphStyle(
            "BodyDark",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#1e293b"),
        ),
        "BodyMuted": ParagraphStyle(
            "BodyMuted",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#64748b"),
        ),
        "CardTitle": ParagraphStyle(
            "CardTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#64748b"),
            alignment=1,
        ),
        "CardValue": ParagraphStyle(
            "CardValue",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=16,
            textColor=colors.HexColor("#0f2942"),
            alignment=1,
        ),
        "CardSub": ParagraphStyle(
            "CardSub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#475569"),
            alignment=1,
        ),
        "TableHeader": ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
            alignment=1,
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=10,
            textColor=colors.HexColor("#1e293b"),
        ),
        "TableCellBold": ParagraphStyle(
            "TableCellBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.8,
            leading=10,
            textColor=colors.HexColor("#0f2942"),
        ),
        "TableCellRight": ParagraphStyle(
            "TableCellRight",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=10,
            textColor=colors.HexColor("#1e293b"),
            alignment=2,
        ),
        "TableCellRightBold": ParagraphStyle(
            "TableCellRightBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.8,
            leading=10,
            textColor=colors.HexColor("#0f2942"),
            alignment=2,
        ),
        "BulletItem": ParagraphStyle(
            "BulletItem",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=10.5,
            textColor=colors.HexColor("#334155"),
            leftIndent=10,
            firstLineIndent=-6,
        ),
    }

    for name, style in custom_styles.items():
        styles.add(style)
    return styles


def criar_bloco_cabecalho(titulo: str, subtitulo: str, styles, largura: float = 523) -> list:
    """Cria o bloco superior institucional com título, subtítulo e metadados."""
    elementos = []

    header_table = Table(
        [
            [
                Paragraph(titulo, styles["DocTitle"]),
                Paragraph("<b>PROJETO CPA</b><br/><font size=7 color='#64748b'>FACULDADE • 2026</font>", styles["TableCellRight"]),
            ],
            [
                Paragraph(subtitulo, styles["DocSubtitle"]),
                Paragraph(f"<font size=7 color='#64748b'>Versão: 1.0 • Status: Concluído</font>", styles["TableCellRight"]),
            ],
        ],
        colWidths=[largura * 0.72, largura * 0.28],
    )
    header_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ])
    )
    elementos.append(header_table)
    elementos.append(Spacer(1, 6))

    # Barra horizontal colorida
    elementos.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2563eb"), spaceBefore=2, spaceAfter=8))

    # Grid de Metadados
    meta_dados = [
        [
            Paragraph("<b>Escopo:</b>", styles["MetaLabel"]),
            Paragraph("Sistema de Comissão Própria de Avaliação (FastAPI + React)", styles["MetaValue"]),
            Paragraph("<b>Nível Analisado:</b>", styles["MetaLabel"]),
            Paragraph("Desenvolvedor Pleno (Fullstack)", styles["MetaValue"]),
        ],
        [
            Paragraph("<b>Stack Técnica:</b>", styles["MetaLabel"]),
            Paragraph("Python, FastAPI, React 18, Google Forms API, Docker", styles["MetaValue"]),
            Paragraph("<b>Base de Testes:</b>", styles["MetaLabel"]),
            Paragraph("157 testes automatizados (unitários + integração)", styles["MetaValue"]),
        ],
    ]
    meta_table = Table(meta_dados, colWidths=[largura * 0.14, largura * 0.40, largura * 0.18, largura * 0.28])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    elementos.append(meta_table)
    elementos.append(Spacer(1, 10))
    return elementos


# ==============================================================================
# GERAÇÃO DO DOCUMENTO 1: RELATÓRIO FINANCEIRO
# ==============================================================================
def gerar_pdf_financeiro(caminho_saida: str):
    """Gera o PDF consolidado com informações financeiras e de tempo."""
    largura = 523
    styles = get_styles()

    doc = SimpleDocTemplate(
        caminho_saida,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=40,
        bottomMargin=42,
    )

    elementos = []
    elementos.extend(
        criar_bloco_cabecalho(
            "Relatório de Estimativa de Custos e Investimento",
            "Dimensionamento Financeiro e Horas de Desenvolvimento — Projeto CPA",
            styles,
            largura,
        )
    )

    # Cards KPI Financeiros
    cards_data = [
        [
            [Paragraph("ESFORÇO TOTAL", styles["CardTitle"]), Paragraph("142 h", styles["CardValue"]), Paragraph("8 fases estruturadas", styles["CardSub"])],
            [Paragraph("TAXA HORÁRIA PJ", styles["CardTitle"]), Paragraph("R$ 80,00", styles["CardValue"]), Paragraph("Mediana de Mercado (Pleno)", styles["CardSub"])],
            [Paragraph("INVESTIMENTO PJ", styles["CardTitle"]), Paragraph("R$ 11.360", styles["CardValue"]), Paragraph("Sem encargos adicionais", styles["CardSub"])],
            [Paragraph("CUSTO EMPRESA CLT", styles["CardTitle"]), Paragraph("R$ 11.644", styles["CardValue"]), Paragraph("Taxa R$ 82/h (fator 1,72x)", styles["CardSub"])],
        ]
    ]
    cards_table = Table(cards_data, colWidths=[largura * 0.25] * 4)
    cards_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#eff6ff")),
            ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#f0fdf4")),
            ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#f8fafc")),
            ("BACKGROUND", (3, 0), (3, 0), colors.HexColor("#fdf4ff")),
            ("BOX", (0, 0), (0, 0), 1, colors.HexColor("#bfdbfe")),
            ("BOX", (1, 0), (1, 0), 1, colors.HexColor("#bbf7d0")),
            ("BOX", (2, 0), (2, 0), 1, colors.HexColor("#cbd5e1")),
            ("BOX", (3, 0), (3, 0), 1, colors.HexColor("#f5d0fe")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    elementos.append(cards_table)
    elementos.append(Spacer(1, 10))

    # Seção 1: Balizadores de Mercado
    elementos.append(Paragraph("1. Balizadores Econômicos e Custo/Hora no Brasil", styles["SectionHeading"]))
    elementos.append(Paragraph(
        "Os cálculos utilizam como referência as métricas vigentes de contratação para um <b>Desenvolvedor Fullstack Pleno</b> "
        "(Python/FastAPI e React) no ecossistema de software brasileiro:",
        styles["BodyDark"],
    ))
    elementos.append(Spacer(1, 4))

    tabela_balizadores_dados = [
        [
            Paragraph("Modelo de Contratação", styles["TableHeader"]),
            Paragraph("Faixa de Mercado (R$/h)", styles["TableHeader"]),
            Paragraph("Valor Adotado (R$/h)", styles["TableHeader"]),
            Paragraph("Composição e Encargos", styles["TableHeader"]),
        ],
        [
            Paragraph("<b>Prestador PJ (Mínimo de Mercado)</b>", styles["TableCell"]),
            Paragraph("R$ 60,00 – R$ 70,00", styles["TableCellRight"]),
            Paragraph("R$ 65,00 / h", styles["TableCellRightBold"]),
            Paragraph("Contrato direto B2B, desenvolvedor pleno inicial.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Prestador PJ (Mediana Recomendada)</b>", styles["TableCell"]),
            Paragraph("R$ 75,00 – R$ 90,00", styles["TableCellRight"]),
            Paragraph("R$ 80,00 / h", styles["TableCellRightBold"]),
            Paragraph("Pleno pleno experiente em integrações complexas e APIs.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Prestador PJ (Teto Especialista)</b>", styles["TableCell"]),
            Paragraph("R$ 90,00 – R$ 105,00", styles["TableCellRight"]),
            Paragraph("R$ 95,00 / h", styles["TableCellRightBold"]),
            Paragraph("Pleno de alto rendimento com domínio de testes e DevOps.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Custo Efetivo Empresa (CLT)</b>", styles["TableCell"]),
            Paragraph("R$ 75,00 – R$ 90,00", styles["TableCellRight"]),
            Paragraph("R$ 82,00 / h", styles["TableCellRightBold"]),
            Paragraph("Salário base R$ 8.000 + encargos FGTS/INSS/férias/13º (fator 1,72x / 168h).", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Software House / Consultoria</b>", styles["TableCell"]),
            Paragraph("R$ 120,00 – R$ 160,00", styles["TableCellRight"]),
            Paragraph("R$ 135,00 / h", styles["TableCellRightBold"]),
            Paragraph("Preço comercial cobrado com margem de lucro, PMO e QA terceirizado.", styles["TableCell"]),
        ],
    ]
    tabela_balizadores = Table(
        tabela_balizadores_dados,
        colWidths=[largura * 0.32, largura * 0.18, largura * 0.18, largura * 0.32],
    )
    tabela_balizadores.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f2942")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    elementos.append(tabela_balizadores)
    elementos.append(Spacer(1, 10))

    # Seção 2: Tabela Orçamentária por Fase
    elementos.append(Paragraph("2. Tabela Orçamentária Consolidada por Fase", styles["SectionHeading"]))
    elementos.append(Paragraph(
        "Demonstrativo de investimento detalhado por fase de desenvolvimento, com taxa de referência de R$ 80,00/h (PJ) "
        "e comparativos de CLT e Consultoria:",
        styles["BodyDark"],
    ))
    elementos.append(Spacer(1, 4))

    tabela_fases_dados = [
        [
            Paragraph("Fase", styles["TableHeader"]),
            Paragraph("Escopo / Módulo Entregue", styles["TableHeader"]),
            Paragraph("Horas", styles["TableHeader"]),
            Paragraph("% Proj.", styles["TableHeader"]),
            Paragraph("Custo PJ (R$ 80/h)", styles["TableHeader"]),
            Paragraph("Custo CLT (R$ 82/h)", styles["TableHeader"]),
            Paragraph("Consultoria (R$ 135/h)", styles["TableHeader"]),
        ],
        [
            Paragraph("<b>Fase 0</b>", styles["TableCellBold"]),
            Paragraph("Esqueleto, Docker e Base Híbrida", styles["TableCell"]),
            Paragraph("8 h", styles["TableCellRight"]),
            Paragraph("5,6%", styles["TableCellRight"]),
            Paragraph("R$ 640,00", styles["TableCellRight"]),
            Paragraph("R$ 656,00", styles["TableCellRight"]),
            Paragraph("R$ 1.080,00", styles["TableCellRight"]),
        ],
        [
            Paragraph("<b>Fase 1</b>", styles["TableCellBold"]),
            Paragraph("Domínio, Cadastros e Perguntas SINAES", styles["TableCell"]),
            Paragraph("18 h", styles["TableCellRight"]),
            Paragraph("12,7%", styles["TableCellRight"]),
            Paragraph("R$ 1.440,00", styles["TableCellRight"]),
            Paragraph("R$ 1.476,00", styles["TableCellRight"]),
            Paragraph("R$ 2.430,00", styles["TableCellRight"]),
        ],
        [
            Paragraph("<b>Fase 2</b>", styles["TableCellBold"]),
            Paragraph("Importador da Grade Horária (XLSX)", styles["TableCell"]),
            Paragraph("26 h", styles["TableCellRight"]),
            Paragraph("18,3%", styles["TableCellRight"]),
            Paragraph("R$ 2.080,00", styles["TableCellRight"]),
            Paragraph("R$ 2.132,00", styles["TableCellRight"]),
            Paragraph("R$ 3.510,00", styles["TableCellRight"]),
        ],
        [
            Paragraph("<b>Fase 3</b>", styles["TableCellBold"]),
            Paragraph("Motor de Formulários, QR Codes e PDFs", styles["TableCell"]),
            Paragraph("18 h", styles["TableCellRight"]),
            Paragraph("12,7%", styles["TableCellRight"]),
            Paragraph("R$ 1.440,00", styles["TableCellRight"]),
            Paragraph("R$ 1.476,00", styles["TableCellRight"]),
            Paragraph("R$ 2.430,00", styles["TableCellRight"]),
        ],
        [
            Paragraph("<b>Fase 4</b>", styles["TableCellBold"]),
            Paragraph("Integração Google Forms API e Ingestão", styles["TableCell"]),
            Paragraph("30 h", styles["TableCellRight"]),
            Paragraph("21,1%", styles["TableCellRight"]),
            Paragraph("R$ 2.400,00", styles["TableCellRight"]),
            Paragraph("R$ 2.460,00", styles["TableCellRight"]),
            Paragraph("R$ 4.050,00", styles["TableCellRight"]),
        ],
        [
            Paragraph("<b>Fase 5/6</b>", styles["TableCellBold"]),
            Paragraph("Métricas ISG, K-Anonimato e Relatórios", styles["TableCell"]),
            Paragraph("20 h", styles["TableCellRight"]),
            Paragraph("14,1%", styles["TableCellRight"]),
            Paragraph("R$ 1.600,00", styles["TableCellRight"]),
            Paragraph("R$ 1.640,00", styles["TableCellRight"]),
            Paragraph("R$ 2.700,00", styles["TableCellRight"]),
        ],
        [
            Paragraph("<b>Fase 7</b>", styles["TableCellBold"]),
            Paragraph("Integração Modo Real e Autenticação", styles["TableCell"]),
            Paragraph("14 h", styles["TableCellRight"]),
            Paragraph("9,9%", styles["TableCellRight"]),
            Paragraph("R$ 1.120,00", styles["TableCellRight"]),
            Paragraph("R$ 1.148,00", styles["TableCellRight"]),
            Paragraph("R$ 1.890,00", styles["TableCellRight"]),
        ],
        [
            Paragraph("<b>Fase 8</b>", styles["TableCellBold"]),
            Paragraph("Deploy, Hardening e Documentação", styles["TableCell"]),
            Paragraph("8 h", styles["TableCellRight"]),
            Paragraph("5,6%", styles["TableCellRight"]),
            Paragraph("R$ 640,00", styles["TableCellRight"]),
            Paragraph("R$ 656,00", styles["TableCellRight"]),
            Paragraph("R$ 1.080,00", styles["TableCellRight"]),
        ],
        [
            Paragraph("<b>TOTAL</b>", styles["TableCellBold"]),
            Paragraph("<b>Projeto CPA — Sistema Completo</b>", styles["TableCellBold"]),
            Paragraph("<b>142 h</b>", styles["TableCellRightBold"]),
            Paragraph("<b>100%</b>", styles["TableCellRightBold"]),
            Paragraph("<b>R$ 11.360,00</b>", styles["TableCellRightBold"]),
            Paragraph("<b>R$ 11.644,00</b>", styles["TableCellRightBold"]),
            Paragraph("<b>R$ 19.170,00</b>", styles["TableCellRightBold"]),
        ],
    ]
    tabela_fases = Table(
        tabela_fases_dados,
        colWidths=[largura * 0.12, largura * 0.34, largura * 0.09, largura * 0.09, largura * 0.12, largura * 0.12, largura * 0.12],
    )
    tabela_fases.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f2942")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8fafc")]),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e2e8f0")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#0f2942")),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    elementos.append(tabela_fases)
    elementos.append(Spacer(1, 10))

    # Quebra de página para o detalhamento fase a fase
    elementos.append(PageBreak())

    # Seção 3: Detalhamento de Custos Tópico por Tópico
    elementos.append(Paragraph("3. Detalhamento dos Tópicos e Custos Associados", styles["SectionHeading"]))
    elementos.append(Paragraph(
        "Discriminação detalhada das entregas de engenharia por fase e seu respectivo valor financeiro alocado:",
        styles["BodyDark"],
    ))
    elementos.append(Spacer(1, 4))

    fases_detalhes = [
        {
            "num": "Fase 0",
            "nome": "Esqueleto, Arquitetura e Orquestração Docker",
            "horas": "8 h",
            "custo": "R$ 640,00",
            "itens": [
                "Setup de ambiente conteinerizado com docker-compose.yml multi-container (backend, frontend e postgres).",
                "Arquitetura de diretórios em FastAPI com injeção de dependências e sessões híbridas SQLAlchemy.",
                "Configuração do Alembic (migrações de esquema) e endpoints de verificação de integridade (GET /api/health).",
                "Scaffold do frontend com React 18, Vite e TailwindCSS com variáveis de ambiente configuráveis.",
            ],
        },
        {
            "num": "Fase 1",
            "nome": "Domínio, Cadastros e Banco de Perguntas (SINAES)",
            "horas": "18 h",
            "custo": "R$ 1.440,00",
            "itens": [
                "Modelos relacionais para Cursos, Disciplinas, Professores, Turmas, Ofertas e Alocações.",
                "Modelagem SINAES: 5 Eixos, 10 Dimensões regulatórias, 67 grupos de equivalência e 163 perguntas do Anexo B.",
                "Desenvolvimento dos scripts de seed complexos e validações relacionais contra duplicatas.",
                "Telas de Cadastros e Banco de Perguntas no React com modal de edição, análise de impacto e filtros.",
                "Suíte de testes de constraints, seeds e integridade referencial.",
            ],
        },
        {
            "num": "Fase 2",
            "nome": "Importador da Grade Horária (XLSX) — Alta Complexidade",
            "horas": "26 h",
            "custo": "R$ 2.080,00",
            "itens": [
                "Leitor em openpyxl tolerante a células mescladas, linhas em branco e cabeçalhos flutuantes.",
                "Gramática léxica de células: separação de cursos, turnos, semestres, turmas divididas (A/B) e ciclo básico.",
                "Pipeline de Staging e Matching fuzzy com tabela de aliases para correção de divergências ortográficas.",
                "Interface de conciliação no frontend com diff interativo antes da confirmação no banco de dados.",
                "Gravação transacional atômica com testes unitários pesados contra a planilha oficial de 2026.2.",
            ],
        },
        {
            "num": "Fase 3",
            "nome": "Motor de Formulários, QR Codes e Artefatos de Impressão",
            "horas": "18 h",
            "custo": "R$ 1.440,00",
            "itens": [
                "Algoritmo de composição dinâmica com snapshot congelado (imunidade a edições posteriores das perguntas).",
                "Expansão automática de blocos por matéria/docente da turma (geração de 48 a 168 perguntas por formulário).",
                "Serviço de geração dinâmica de QR Codes em PNG e SVG vetorial.",
                "Geração de artefatos de impressão em PDF (ReportLab): folhas A4 de aplicação por turma, listas e cartazes.",
                "Telas no frontend para gestão de formulários e visualização prévia diagramada.",
            ],
        },
        {
            "num": "Fase 4",
            "nome": "Integração com Google Forms API — Alta Complexidade",
            "horas": "30 h",
            "custo": "R$ 2.400,00",
            "itens": [
                "Autenticação corporativa via Google Cloud Service Account com delegação de autoridade.",
                "Sincronizador em lote: batchUpdate atômico com questionGroupItem (Likert) e pageBreakItem por dimensão.",
                "Segurança e garantia de anonimato: imposição e releitura estrita de emailCollectionType = DO_NOT_COLLECT.",
                "Ingestor assíncrono de respostas: mapeamento de google_question_id, idempotência e tratamento de órfãs.",
                "Telas de sincronização e prévia com diff antes do sync e testes automatizados com API dublê.",
            ],
        },
        {
            "num": "Fase 5/6",
            "nome": "Métricas ISG, K-Anonimato e Relatórios Analíticos",
            "horas": "20 h",
            "custo": "R$ 1.600,00",
            "itens": [
                "Implementação da fórmula oficial do ISG (Índice de Satisfação Geral) com agregação agregada (pooled).",
                "Algoritmo de k-anonimato: supressão de amostras para turmas < 5 respostas e restrição detalhada para < 10.",
                "Endpoints analíticos com agregações multidimensionais (segmento, dimensão SINAES, eixo, turma e docente).",
                "Módulo de exportação de dados higienizados em CSV estruturado.",
                "Frontend analítico: Dashboard com métricas globais e tela de relatórios com filtros avançados.",
            ],
        },
        {
            "num": "Fase 7",
            "nome": "Integração do Painel em Modo Real e Autenticação",
            "horas": "14 h",
            "custo": "R$ 1.120,00",
            "itens": [
                "Desativação de mocks (VITE_USE_MOCK = false) e conexão com todas as APIs reais do FastAPI.",
                "Sistema de autenticação administrativa (Basic Auth segura, sessionStorage e proteção de rotas).",
                "Enriquecimento de DTOs no backend com contadores consolidados e tratamento robusto de erros de rede.",
                "Validação tela a tela da conciliação, prévia e geração contra o banco real.",
            ],
        },
        {
            "num": "Fase 8",
            "nome": "Preparação para Deploy, Hardening e Documentação",
            "horas": "8 h",
            "custo": "R$ 640,00",
            "itens": [
                "Empacotamento de produção: Dockerfile multi-stage com Nginx no frontend e imagem leve no backend.",
                "Configuração do Supabase (pooling de conexões) e Render com variáveis de ambiente protegidas.",
                "Restrição de CORS, proteção de credenciais e checklist de segurança.",
                "Roteiro de homologação operacional e manual de ciclo para a comissão da CPA.",
            ],
        },
    ]

    for f in fases_detalhes:
        bloco_fase = []
        cabecalho_fase = Table(
            [
                [
                    Paragraph(f"<b>{f['num']} — {f['nome']}</b>", styles["SubsectionHeading"]),
                    Paragraph(f"<b>{f['horas']}</b> | <font color='#059669'><b>{f['custo']}</b></font>", styles["TableCellRightBold"]),
                ]
            ],
            colWidths=[largura * 0.72, largura * 0.28],
        )
        cabecalho_fase.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
        )
        bloco_fase.append(cabecalho_fase)
        for it in f["itens"]:
            bloco_fase.append(Paragraph(f"• {it}", styles["BulletItem"]))
        bloco_fase.append(Spacer(1, 4))
        elementos.append(KeepTogether(bloco_fase))

    # Seção 4: Síntese e ROI de Infraestrutura
    elementos.append(Spacer(1, 4))
    elementos.append(Paragraph("4. Considerações de ROI e Infraestrutura", styles["SectionHeading"]))
    obs_text = (
        "<b>Otimização de Custos Fixos Recorrentes:</b> O projeto foi desenhado sob a premissa de <b>custo zero de hospedagem e infraestrutura</b>. "
        "O frontend opera na camada gratuita da Vercel, o backend no plano gratuito do Render e o banco de dados no Supabase (PostgreSQL gerenciado). "
        "A substituição do portal do aluno pelo Google Forms gera economia de servidores de alta concorrência durante a semana de avaliação da CPA. "
        "Portanto, o investimento financeiro total restringe-se estritamente às horas de engenharia de desenvolvimento."
    )
    obs_table = Table([[Paragraph(obs_text, styles["BodyDark"])]], colWidths=[largura])
    obs_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#ecfdf5")),
            ("BOX", (0, 0), (0, 0), 1, colors.HexColor("#a7f3d0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    elementos.append(obs_table)

    doc.build(elementos, canvasmaker=lambda *a, **k: NumberedCanvas(*a, **k))
    print(f"PDF Financeiro gerado com sucesso: {caminho_saida}")


# ==============================================================================
# GERAÇÃO DO DOCUMENTO 2: RELATÓRIO TÉCNICO DE TEMPO E ESCOPO
# ==============================================================================
def gerar_pdf_tempo(caminho_saida: str):
    """Gera o PDF consolidado com informações exclusivas de tempo e engenharia."""
    largura = 523
    styles = get_styles()

    doc = SimpleDocTemplate(
        caminho_saida,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=40,
        bottomMargin=42,
    )

    elementos = []
    elementos.extend(
        criar_bloco_cabecalho(
            "Relatório Técnico de Tempo e Cronograma",
            "Mapeamento de Esforço de Engenharia e Prazos — Projeto CPA",
            styles,
            largura,
        )
    )

    # Cards KPI Técnicos
    cards_data = [
        [
            [Paragraph("ESFORÇO ESTIMADO", styles["CardTitle"]), Paragraph("142 h", styles["CardValue"]), Paragraph("Horas produtivas líquidas", styles["CardSub"])],
            [Paragraph("DURAÇÃO CALENDÁRIO", styles["CardTitle"]), Paragraph("3,5 a 4 sem", styles["CardValue"]), Paragraph("Dedicação integral (40h/sem)", styles["CardSub"])],
            [Paragraph("TOTAL DE FASES", styles["CardTitle"]), Paragraph("8 Fases", styles["CardValue"]), Paragraph("Fase 0 à Fase 8 concluídas", styles["CardSub"])],
            [Paragraph("COBERTURA DE TESTES", styles["CardTitle"]), Paragraph("157 Casos", styles["CardValue"]), Paragraph("Unitários + Integração", styles["CardSub"])],
        ]
    ]
    cards_table = Table(cards_data, colWidths=[largura * 0.25] * 4)
    cards_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#f8fafc")),
            ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#eff6ff")),
            ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#f0fdf4")),
            ("BACKGROUND", (3, 0), (3, 0), colors.HexColor("#fefce8")),
            ("BOX", (0, 0), (0, 0), 1, colors.HexColor("#cbd5e1")),
            ("BOX", (1, 0), (1, 0), 1, colors.HexColor("#bfdbfe")),
            ("BOX", (2, 0), (2, 0), 1, colors.HexColor("#bbf7d0")),
            ("BOX", (3, 0), (3, 0), 1, colors.HexColor("#fef08a")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    elementos.append(cards_table)
    elementos.append(Spacer(1, 10))

    # Seção 1: Matriz de Distribuição Temporal e Complexidade
    elementos.append(Paragraph("1. Matriz de Distribuição Temporal e Nível de Risco", styles["SectionHeading"]))
    elementos.append(Paragraph(
        "Mapeamento do esforço de engenharia por fase com classificação de risco e dias úteis correspondentes:",
        styles["BodyDark"],
    ))
    elementos.append(Spacer(1, 4))

    tabela_tempo_dados = [
        [
            Paragraph("Fase", styles["TableHeader"]),
            Paragraph("Módulo / Escopo Principal", styles["TableHeader"]),
            Paragraph("Complexidade", styles["TableHeader"]),
            Paragraph("Horas (h)", styles["TableHeader"]),
            Paragraph("Dias Úteis", styles["TableHeader"]),
            Paragraph("% Esforço", styles["TableHeader"]),
            Paragraph("Status de Entrega", styles["TableHeader"]),
        ],
        [
            Paragraph("<b>Fase 0</b>", styles["TableCellBold"]),
            Paragraph("Esqueleto, Docker e Base Híbrida", styles["TableCell"]),
            Paragraph("<font color='#0284c7'><b>Baixa</b></font>", styles["TableCell"]),
            Paragraph("8 h", styles["TableCellRight"]),
            Paragraph("1,0 dia", styles["TableCellRight"]),
            Paragraph("5,6%", styles["TableCellRight"]),
            Paragraph("<font color='#059669'>Concluída</font>", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Fase 1</b>", styles["TableCellBold"]),
            Paragraph("Domínio, Cadastros e Perguntas SINAES", styles["TableCell"]),
            Paragraph("<font color='#2563eb'><b>Média</b></font>", styles["TableCell"]),
            Paragraph("18 h", styles["TableCellRight"]),
            Paragraph("2,25 dias", styles["TableCellRight"]),
            Paragraph("12,7%", styles["TableCellRight"]),
            Paragraph("<font color='#059669'>Concluída</font>", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Fase 2</b>", styles["TableCellBold"]),
            Paragraph("Importador da Grade Horária (XLSX)", styles["TableCell"]),
            Paragraph("<font color='#dc2626'><b>Crítica / Alta</b></font>", styles["TableCell"]),
            Paragraph("26 h", styles["TableCellRight"]),
            Paragraph("3,25 dias", styles["TableCellRight"]),
            Paragraph("18,3%", styles["TableCellRight"]),
            Paragraph("<font color='#059669'>Concluída</font>", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Fase 3</b>", styles["TableCellBold"]),
            Paragraph("Motor de Formulários, QR Codes e PDFs", styles["TableCell"]),
            Paragraph("<font color='#2563eb'><b>Média</b></font>", styles["TableCell"]),
            Paragraph("18 h", styles["TableCellRight"]),
            Paragraph("2,25 dias", styles["TableCellRight"]),
            Paragraph("12,7%", styles["TableCellRight"]),
            Paragraph("<font color='#059669'>Concluída</font>", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Fase 4</b>", styles["TableCellBold"]),
            Paragraph("Integração Google Forms API e Ingestão", styles["TableCell"]),
            Paragraph("<font color='#dc2626'><b>Crítica / Alta</b></font>", styles["TableCell"]),
            Paragraph("30 h", styles["TableCellRight"]),
            Paragraph("3,75 dias", styles["TableCellRight"]),
            Paragraph("21,1%", styles["TableCellRight"]),
            Paragraph("<font color='#059669'>Concluída</font>", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Fase 5/6</b>", styles["TableCellBold"]),
            Paragraph("Métricas ISG, K-Anonimato e Relatórios", styles["TableCell"]),
            Paragraph("<font color='#d97706'><b>Média-Alta</b></font>", styles["TableCell"]),
            Paragraph("20 h", styles["TableCellRight"]),
            Paragraph("2,5 dias", styles["TableCellRight"]),
            Paragraph("14,1%", styles["TableCellRight"]),
            Paragraph("<font color='#059669'>Concluída</font>", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Fase 7</b>", styles["TableCellBold"]),
            Paragraph("Integração Modo Real e Autenticação", styles["TableCell"]),
            Paragraph("<font color='#2563eb'><b>Média</b></font>", styles["TableCell"]),
            Paragraph("14 h", styles["TableCellRight"]),
            Paragraph("1,75 dias", styles["TableCellRight"]),
            Paragraph("9,9%", styles["TableCellRight"]),
            Paragraph("<font color='#059669'>Concluída</font>", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Fase 8</b>", styles["TableCellBold"]),
            Paragraph("Deploy, Hardening e Documentação", styles["TableCell"]),
            Paragraph("<font color='#0284c7'><b>Baixa</b></font>", styles["TableCell"]),
            Paragraph("8 h", styles["TableCellRight"]),
            Paragraph("1,0 dia", styles["TableCellRight"]),
            Paragraph("5,6%", styles["TableCellRight"]),
            Paragraph("<font color='#059669'>Concluída</font>", styles["TableCell"]),
        ],
        [
            Paragraph("<b>TOTAL</b>", styles["TableCellBold"]),
            Paragraph("<b>Projeto CPA — Esforço Total</b>", styles["TableCellBold"]),
            Paragraph("<b>—</b>", styles["TableCell"]),
            Paragraph("<b>142 h</b>", styles["TableCellRightBold"]),
            Paragraph("<b>17,75 dias</b>", styles["TableCellRightBold"]),
            Paragraph("<b>100%</b>", styles["TableCellRightBold"]),
            Paragraph("<font color='#059669'><b>Homologado</b></font>", styles["TableCellBold"]),
        ],
    ]
    tabela_tempo = Table(
        tabela_tempo_dados,
        colWidths=[largura * 0.11, largura * 0.33, largura * 0.14, largura * 0.10, largura * 0.11, largura * 0.10, largura * 0.11],
    )
    tabela_tempo.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f2942")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8fafc")]),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e2e8f0")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#0f2942")),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    elementos.append(tabela_tempo)
    elementos.append(Spacer(1, 10))

    # Quebra de página para o detalhamento técnico
    elementos.append(PageBreak())

    # Seção 2: Detalhamento Técnico de Engenharia por Fase
    elementos.append(Paragraph("2. Detalhamento de Engenharia Tópico por Tópico", styles["SectionHeading"]))
    elementos.append(Paragraph(
        "Mapeamento aprofundado dos requisitos atendidos, arquitetura e componentes desenvolvidos em cada etapa:",
        styles["BodyDark"],
    ))
    elementos.append(Spacer(1, 4))

    fases_detalhes_tempo = [
        {
            "num": "Fase 0",
            "nome": "Esqueleto, Arquitetura e Orquestração Docker",
            "horas": "8 h (1 dia)",
            "complexidade": "Baixa Complexidade",
            "itens": [
                "Configuração do ecossistema conteinerizado via Docker Compose (FastAPI, React Vite, PostgreSQL local).",
                "Arquitetura modular em camadas no backend: core, api, models, schemas, services e db.",
                "Integração do motor de migrações Alembic com suporte híbrido (Docker local e nuvem Supabase).",
                "Endpoints de healthcheck ativos (GET /api/health) e parametrização segura de variáveis (.env.example).",
            ],
        },
        {
            "num": "Fase 1",
            "nome": "Domínio, Cadastros e Banco de Perguntas (SINAES)",
            "horas": "18 h (2,25 dias)",
            "complexidade": "Média Complexidade",
            "itens": [
                "Mapeamento relacional completo: Cursos, Disciplinas, Professores, Turmas, Ofertas e Alocações.",
                "Carga da base SINAES: 5 Eixos, 10 Dimensões regulatórias, 67 grupos de equivalência e 163 perguntas do Anexo B.",
                "Desenvolvimento dos scripts automatizados de seed com constraints contra duplicação de dados.",
                "Construção de CRUDs administrativos e telas interativas com modal de edição e análise de impacto no React.",
                "Testes automatizados de validação de schemas Pydantic e integridade de chave estrangeira.",
            ],
        },
        {
            "num": "Fase 2",
            "nome": "Importador da Grade Horária (XLSX) — Maior Risco de Domínio",
            "horas": "26 h (3,25 dias)",
            "complexidade": "Alta Complexidade / Crítica",
            "itens": [
                "Desenvolvimento de parser resiliente em openpyxl para planilhas sem padrão estrito e células mescladas.",
                "Motor léxico e sintático de células: extração de turnos, períodos, turmas compostas (A/B) e ciclo básico unificado.",
                "Pipeline de Staging e Matching fuzzy tolerante com catálogo de aliases de docentes para conciliação de nomes.",
                "Interface de conciliação no frontend para resolução assistida de pendências e conferência visual de diff.",
                "Efetivação transacional idempotente (reimportações repetidas geram diff nulo e zero duplicatas).",
                "Cobertura de testes unitários pesados validando a planilha de 2026.2 (17 turmas, 105 ofertas, 164 alocações).",
            ],
        },
        {
            "num": "Fase 3",
            "nome": "Motor de Formulários, QR Codes e Artefatos Físicos",
            "horas": "18 h (2,25 dias)",
            "complexidade": "Média Complexidade",
            "itens": [
                "Algoritmo de snapshot congelado de perguntas: imunidade retroativa após a geração do questionário.",
                "Composição dinâmica dos 4 instrumentos (Discente, Docente, Técnico e Autoavaliação) com blocos por matéria.",
                "Microserviço de geração e renderização de QR Codes em PNG e formato vetorial SVG.",
                "Gerador de documentos PDF para impressão física (ReportLab): folha de aplicação A4 por turma, listas e cartazes.",
                "Painel de formulários e visualizador de prévia paginada com quebras por dimensão e matéria.",
            ],
        },
        {
            "num": "Fase 4",
            "nome": "Integração com Google Forms API — Maior Risco Técnico",
            "horas": "30 h (3,75 dias)",
            "complexidade": "Alta Complexidade / Crítica",
            "itens": [
                "Autenticação corporativa via Google Cloud Service Account com delegação de autoridade no Google Drive.",
                "Sincronizador em lote: batchUpdate com questionGroupItem (grades Likert) e pageBreakItem por dimensão.",
                "Mecanismo estrito de anonimato: afirmação e releitura mandante de emailCollectionType = DO_NOT_COLLECT.",
                "Ingestão incremental e assíncrona de respostas, mapeamento por questionId e tratamento de formulários órfãos.",
                "Tela de prévia com cálculo de diff estrutural antes de enviar alterações para o Google.",
                "Testes com dublê de API do Google Forms (falso_google.py) garantindo idempotência e resiliência de rede.",
            ],
        },
        {
            "num": "Fase 5/6",
            "nome": "Métricas ISG, K-Anonimato e Relatórios Analíticos",
            "horas": "20 h (2,5 dias)",
            "complexidade": "Média-Alta Complexidade",
            "itens": [
                "Implementação da fórmula estatística do ISG (Índice de Satisfação Geral) com agregação pooled confiável.",
                "Mecanismo de proteção de k-anonimato: supressão visual de ofertas com menos de 5 submissões (amostra insuficiente).",
                "Consultas analíticas agrupadas por segmento, dimensão SINAES, eixo institucional, turma e docente.",
                "Pipeline de higienização e exportação de relatórios em CSV sem expor metadados individuais.",
                "Painel do Dashboard com KPIs consolidados e módulo de relatórios com gráficos dinâmicos.",
            ],
        },
        {
            "num": "Fase 7",
            "nome": "Ligar Painel ao Backend (Modo Real) e Autenticação",
            "horas": "14 h (1,75 dias)",
            "complexidade": "Média Complexidade",
            "itens": [
                "Desativação definitiva de mocks estáticos e consumo das APIs reais do FastAPI em todas as 8 telas.",
                "Sistema de autenticação administrativa (Basic Auth com criptografia, sessionStorage e rotas protegidas).",
                "Enriquecimento de schemas DTO com contadores agregados, rótulos descritivos e prevenção de corrida de dados.",
                "Validação ponta a ponta dos fluxos de conciliação, prévia e acompanhamento com o banco real.",
            ],
        },
        {
            "num": "Fase 8",
            "nome": "Preparação para Deploy, Hardening e Documentação",
            "horas": "8 h (1 dia)",
            "complexidade": "Baixa Complexidade",
            "itens": [
                "Otimização de build: multi-stage Dockerfile para Vite/Nginx e imagem otimizada em Python 3.12 no Render.",
                "Configuração do Supabase (pooling de conexões) e isolamento rigoroso de variáveis de ambiente (.env).",
                "Políticas restritas de CORS, sanitização de logs e contingência para hibernação do tier gratuito.",
                "Documentação operacional passo a passo para a comissão da CPA (importar -> gerar -> coletar -> relatórios).",
            ],
        },
    ]

    for f in fases_detalhes_tempo:
        bloco_fase = []
        cabecalho_fase = Table(
            [
                [
                    Paragraph(f"<b>{f['num']} — {f['nome']}</b>", styles["SubsectionHeading"]),
                    Paragraph(f"<b>{f['horas']}</b> | <font color='#2563eb'><b>{f['complexidade']}</b></font>", styles["TableCellRightBold"]),
                ]
            ],
            colWidths=[largura * 0.68, largura * 0.32],
        )
        cabecalho_fase.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
        )
        bloco_fase.append(cabecalho_fase)
        for it in f["itens"]:
            bloco_fase.append(Paragraph(f"• {it}", styles["BulletItem"]))
        bloco_fase.append(Spacer(1, 4))
        elementos.append(KeepTogether(bloco_fase))

    # Seção 3: Cronograma e Marcos de Aceite (Definition of Done)
    elementos.append(Spacer(1, 4))
    elementos.append(Paragraph("3. Marcos de Aceite Técnico e Definition of Done", styles["SectionHeading"]))
    criterios = (
        "<b>Critérios Obrigatórios Cumpridos:</b><br/>"
        "1. <b>Automação Docker:</b> O comando <code>docker compose up</code> orquestra backend, frontend e banco sem intervenção.<br/>"
        "2. <b>Resiliência da Grade:</b> 100% de conformidade contra o arquivo real de 2026.2 (17 turmas, 105 ofertas e 164 alocações).<br/>"
        "3. <b>Imunidade Regulamentar:</b> Snapshot congelado dos 4 instrumentos com 163 perguntas e 67 grupos de equivalência SINAES.<br/>"
        "4. <b>Garantia de Anonimato:</b> Bloqueio automático de publicação caso <code>emailCollectionType != DO_NOT_COLLECT</code>.<br/>"
        "5. <b>Proteção Estatística:</b> Cálculo do ISG pooled e salvaguarda de k-anonimato com supressão para amostras &lt; 5 respostas."
    )
    criterios_table = Table([[Paragraph(criterios, styles["BodyDark"])]], colWidths=[largura])
    criterios_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#f0fdf4")),
            ("BOX", (0, 0), (0, 0), 1, colors.HexColor("#bbf7d0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    elementos.append(criterios_table)

    doc.build(elementos, canvasmaker=lambda *a, **k: NumberedCanvas(*a, **k))
    print(f"PDF de Tempo gerado com sucesso: {caminho_saida}")


if __name__ == "__main__":
    dir_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    saida_financeira = os.path.join(dir_raiz, "relatorio_estimativa_financeira_cpa.pdf")
    saida_tempo = os.path.join(dir_raiz, "relatorio_estimativa_tempo_cpa.pdf")

    gerar_pdf_financeiro(saida_financeira)
    gerar_pdf_tempo(saida_tempo)
