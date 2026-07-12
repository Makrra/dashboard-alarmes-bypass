"""PDF didatico de Bypass: resumo executivo + secoes detalhadas para os
bypasses mais relevantes (maior tempo total em bypass)."""

from collections import defaultdict

from reportlab.lib.units import cm
from reportlab.platypus import Spacer, PageBreak, Paragraph

import classificar_bypass
import pdf_comum
import pdf_graficos
from sessoes import formatar_duracao

TOP_N = 15
TOP_N_GRAFICO = 10


def _tag_curta(tag, tamanho=24):
    return tag if len(tag) <= tamanho else tag[: tamanho - 1] + "…"


def _sessoes_por_tag(sessoes_bypass):
    por_tag = defaultdict(list)
    for s in sessoes_bypass:
        por_tag[s["chave"]].append(s)
    for lista in por_tag.values():
        lista.sort(key=lambda s: s["inicio"])
    return por_tag


def _linha_sessao(s):
    inicio = s["inicio"].strftime("%d/%m %H:%M:%S")
    fim = s["fim"].strftime("%d/%m %H:%M:%S") if s["fim"] else "Em aberto"
    return [inicio, s["operador_abertura"] or "-", fim, s["operador_fechamento"] or "-", s["duracao_fmt"]]


def _texto_narrativo(r):
    partes = [
        f'Este bypass foi ativado <b>{r["qtd_ativacoes"]}</b> vez(es) no periodo analisado, '
        f'permanecendo em bypass por um total de <b>{r["tempo_total_bypass_fmt"]}</b>.'
    ]
    if r["operadores_resumo"]:
        partes.append(f'Operador(es) responsavel(is) pela ativacao: {r["operadores_resumo"]}.')
    if r["qtd_ainda_ativo"]:
        partes.append("Este bypass permanece ativo no momento do fechamento do periodo analisado.")
    return " ".join(partes)


def gerar(caminho_saida, resumo_bypass, sessoes_bypass, periodo_texto):
    doc = pdf_comum.novo_documento(caminho_saida)
    story = []

    total_tags = len(resumo_bypass)
    total_ativacoes = sum(r["qtd_ativacoes"] for r in resumo_bypass)
    total_ainda_ativo = sum(r["qtd_ainda_ativo"] for r in resumo_bypass)
    tempo_total_geral = sum(r["tempo_total_bypass_s"] for r in resumo_bypass)

    pdf_comum.cabecalho(
        story, "Relatorio de Bypass", periodo_texto,
        "Este relatorio resume as ativacoes de bypass registradas no periodo, "
        "indicando quando cada bypass foi ativado, por qual operador, quando foi "
        "retirado e por quanto tempo permaneceu ativo."
    )

    story.append(pdf_comum.tabela_kpis([
        ("Tags de bypass distintas", str(total_tags)),
        ("Total de ativacoes", str(total_ativacoes)),
        ("Ainda em bypass ao final do periodo", str(total_ainda_ativo)),
        ("Tempo total em bypass (soma de todos)", formatar_duracao(tempo_total_geral)),
    ]))
    story.append(Spacer(1, 14))

    por_operador = classificar_bypass.contagem_por_operador(sessoes_bypass)[:TOP_N_GRAFICO]
    if por_operador:
        story.append(Paragraph(
            "Ativacoes de bypass por operador (rastreabilidade)",
            pdf_comum.styles["SecaoTitulo"],
        ))
        story.append(pdf_graficos.grafico_barras_horizontais(
            [op for op, _ in reversed(por_operador)],
            [qtd for _, qtd in reversed(por_operador)],
            rotulo_fmt="%.0f",
        ))
        story.append(Spacer(1, 10))

    resumo_ordenado = sorted(resumo_bypass, key=lambda r: -r["tempo_total_bypass_s"])
    top = resumo_ordenado[:TOP_N]
    top_grafico = resumo_ordenado[:TOP_N_GRAFICO]

    story.append(Paragraph(
        f"Top {len(top_grafico)} bypass por tempo total ativo",
        pdf_comum.styles["SecaoTitulo"],
    ))
    story.append(pdf_graficos.grafico_barras_horizontais(
        [_tag_curta(r["tag"]) for r in reversed(top_grafico)],
        [r["tempo_total_bypass_s"] / 3600 for r in reversed(top_grafico)],
        rotulo_fmt="%.0fh",
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        f"Ranking - Top {len(top)} bypass por tempo total ativo",
        pdf_comum.styles["SecaoTitulo"],
    ))
    linhas_ranking = [
        [r["tag"], r["descricao"][:34], str(r["qtd_ativacoes"]),
         r["tempo_total_bypass_fmt"], r["operadores_resumo"][:24]]
        for r in top
    ]
    story.append(pdf_comum.tabela_ranking(
        ["Tag", "Descricao", "Ativacoes", "Tempo total", "Operadores"],
        linhas_ranking,
        [3.0 * cm, 6.2 * cm, 2.2 * cm, 2.6 * cm, 4.0 * cm],
    ))

    story.append(PageBreak())
    por_tag = _sessoes_por_tag(sessoes_bypass)
    for r in top:
        sessoes_tag = por_tag.get(r["tag"], [])
        linhas = [_linha_sessao(s) for s in sessoes_tag]
        idx_ativos = [i for i, s in enumerate(sessoes_tag) if s["status"] == "ATIVO (em aberto)"]
        tabela = pdf_comum.tabela_sessoes(
            ["Ativado em", "Operador (ativacao)", "Retirado em", "Operador (retirada)", "Duracao"],
            linhas,
            [3.2 * cm, 3.3 * cm, 3.2 * cm, 3.3 * cm, 3.4 * cm],
            linhas_ativas=idx_ativos,
        )
        nota = None
        if r["qtd_ainda_ativo"]:
            nota = pdf_comum.nota_box(
                "Atencao", "Este bypass permanece ativo ao final do periodo analisado."
            )
        pdf_comum.secao_tag(story, r["tag"], r["descricao"], _texto_narrativo(r), tabela, nota)

    doc.build(story)
