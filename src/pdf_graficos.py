"""Graficos nativos para os PDFs (reportlab.graphics), sem dependencia de
matplotlib - mantem o executavel empacotado leve e sem imagens rasterizadas."""

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend

COR_BARRA = colors.HexColor("#2E75B6")
COR_RECONHECIDO = colors.HexColor("#548235")
COR_SOZINHO = colors.HexColor("#C00000")
COR_ATIVO = colors.HexColor("#ED7D31")


def grafico_barras_horizontais(categorias, valores, largura=17.6 * cm, rotulo_fmt="%.1f"):
    """Ranking em barras horizontais (categorias longas ficam mais legiveis
    do que em barras verticais). Ordem: primeira categoria no topo."""
    categorias = list(categorias)
    valores = list(valores)
    n = max(len(categorias), 1)
    altura_por_barra = 0.75 * cm
    altura = n * altura_por_barra + 1 * cm

    d = Drawing(largura, altura)
    chart = HorizontalBarChart()
    chart.x = 4.6 * cm
    chart.y = 0.3 * cm
    chart.width = largura - 6.2 * cm
    chart.height = altura - 0.6 * cm
    chart.data = [valores]
    chart.categoryAxis.categoryNames = categorias
    chart.categoryAxis.labels.fontSize = 8
    chart.categoryAxis.labels.fillColor = colors.HexColor("#404040")
    chart.valueAxis.valueMin = 0
    chart.valueAxis.labels.fontSize = 7.5
    chart.bars[0].fillColor = COR_BARRA
    chart.barLabels.fontSize = 7.5
    chart.barLabelFormat = rotulo_fmt
    chart.barLabels.nudge = 8
    chart.barWidth = 0.55 * cm
    d.add(chart)
    return d


def grafico_pizza(labels, valores, cores, largura=17.6 * cm, altura=5.2 * cm):
    """Grafico de pizza com legenda ao lado, para distribuicoes com poucas
    categorias (ex: reconhecido / retornou sozinho / ainda ativo)."""
    d = Drawing(largura, altura)
    pie = Pie()
    pie.x = 0.4 * cm
    pie.y = 0.3 * cm
    pie.width = 4.6 * cm
    pie.height = 4.6 * cm
    pie.data = [max(v, 0.0001) for v in valores]
    pie.simpleLabels = False
    pie.slices.strokeWidth = 0.75
    pie.slices.strokeColor = colors.white
    for i, cor in enumerate(cores):
        pie.slices[i].fillColor = cor
    d.add(pie)

    legend = Legend()
    legend.x = 6.2 * cm
    legend.y = altura - 0.6 * cm
    legend.dx = 8
    legend.dy = 8
    legend.dxTextSpace = 6
    legend.deltay = 14
    legend.fontName = "Helvetica"
    legend.fontSize = 9
    legend.alignment = "left"
    legend.colorNamePairs = [
        (cor, f"{label}: {int(valor)}") for cor, label, valor in zip(cores, labels, valores)
    ]
    d.add(legend)
    return d
