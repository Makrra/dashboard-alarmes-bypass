"""Estilos e helpers de PDF compartilhados entre os relatorios de alarmes e
de bypass. Reaproveita a paleta e a estrutura ja validada em
gerar_relatorio_bypasses_pdf.py do projeto irmao."""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
)

AZUL_ESCURO = colors.HexColor("#1F3864")
CINZA_CLARO = colors.HexColor("#F2F2F2")
DESTAQUE = colors.HexColor("#FFE699")
VERMELHO_BG = colors.HexColor("#FFC7CE")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TituloRel", fontSize=17, leading=21,
                           textColor=AZUL_ESCURO, spaceAfter=4,
                           alignment=TA_CENTER, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle(name="SubtituloRel", fontSize=10.5, leading=14,
                           textColor=colors.grey, spaceAfter=12,
                           alignment=TA_CENTER))
styles.add(ParagraphStyle(name="SecaoTitulo", fontSize=13, leading=17,
                           textColor=AZUL_ESCURO, spaceBefore=14, spaceAfter=6,
                           fontName="Helvetica-Bold"))
styles.add(ParagraphStyle(name="TagTitulo", fontSize=12.5, leading=20,
                           textColor=colors.white, fontName="Helvetica-Bold",
                           backColor=AZUL_ESCURO, spaceBefore=10, spaceAfter=4,
                           leftIndent=6))
styles.add(ParagraphStyle(name="Descricao", fontSize=9.5, leading=13,
                           textColor=colors.HexColor("#404040"),
                           spaceBefore=2, spaceAfter=8,
                           fontName="Helvetica-Oblique"))
styles.add(ParagraphStyle(name="Corpo", fontSize=10, leading=14,
                           alignment=TA_JUSTIFY, spaceAfter=6))
styles.add(ParagraphStyle(name="Nota", fontSize=9.5, leading=13,
                           alignment=TA_JUSTIFY))
styles.add(ParagraphStyle(name="Legenda", fontSize=8, leading=10.5,
                           textColor=colors.grey, spaceBefore=12))


def novo_documento(caminho_saida):
    return SimpleDocTemplate(
        caminho_saida, pagesize=A4,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        leftMargin=1.6 * cm, rightMargin=1.6 * cm,
    )


def cabecalho(story, titulo, subtitulo, intro):
    story.append(Paragraph(titulo, styles["TituloRel"]))
    story.append(Paragraph(subtitulo, styles["SubtituloRel"]))
    story.append(HRFlowable(width="100%", thickness=1, color=AZUL_ESCURO, spaceAfter=10))
    story.append(Paragraph(intro, styles["Corpo"]))
    story.append(Spacer(1, 6))


def tabela_kpis(pares):
    """pares: lista de (rotulo, valor)."""
    dados = [[rotulo, valor] for rotulo, valor in pares]
    t = Table(dados, colWidths=[9 * cm, 8 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFBFBF")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, CINZA_CLARO]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def tabela_ranking(cabecalhos, linhas, larguras):
    dados = [cabecalhos] + linhas
    t = Table(dados, colWidths=larguras, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL_ESCURO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFBFBF")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CINZA_CLARO]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def tabela_sessoes(cabecalhos, linhas, larguras, linhas_ativas=None):
    dados = [cabecalhos] + linhas
    t = Table(dados, colWidths=larguras, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL_ESCURO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFBFBF")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CINZA_CLARO]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if linhas_ativas:
        for idx in linhas_ativas:
            style.append(("BACKGROUND", (0, idx + 1), (-1, idx + 1), VERMELHO_BG))
            style.append(("FONTNAME", (0, idx + 1), (-1, idx + 1), "Helvetica-Bold"))
    t.setStyle(TableStyle(style))
    return t


def nota_box(titulo, texto, largura=17.8 * cm):
    conteudo = f"<font color='#C55A11'><b>{titulo}:</b></font> {texto}"
    p = Paragraph(conteudo, styles["Nota"])
    t = Table([[p]], colWidths=[largura])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF6E5")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#F4B183")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def secao_tag(story, tag, descricao, texto, tabela, nota=None):
    story.append(Paragraph(tag, styles["TagTitulo"]))
    story.append(Paragraph(f'Descricao SCADA: "{descricao}"', styles["Descricao"]))
    story.append(Paragraph(texto, styles["Corpo"]))
    story.append(tabela)
    if nota:
        story.append(Spacer(1, 4))
        story.append(nota)
    story.append(Spacer(1, 10))
