"""PDF didatico de Alarmes: resumo executivo + secoes detalhadas para os
alarmes mais relevantes (maior tempo total atuado)."""

from collections import defaultdict

from reportlab.lib.units import cm
from reportlab.platypus import Spacer, PageBreak, Paragraph

import classificar_alarmes
import pdf_comum
import pdf_graficos
from sessoes import formatar_duracao

TOP_N = 15
TOP_N_GRAFICO = 10


def _tag_curta(tag, tamanho=24):
    return tag if len(tag) <= tamanho else tag[: tamanho - 1] + "…"


def _sessoes_por_tag(sessoes_alarmes):
    por_tag = defaultdict(list)
    for s in sessoes_alarmes:
        por_tag[s["chave"]].append(s)
    for lista in por_tag.values():
        lista.sort(key=lambda s: s["inicio"])
    return por_tag


def _linha_sessao(s):
    inicio = s["inicio"].strftime("%d/%m %H:%M:%S")
    fim = s["fim"].strftime("%d/%m %H:%M:%S") if s["fim"] else "Em aberto"
    ack = s["ack_em"].strftime("%d/%m %H:%M:%S") if s["ack_em"] else "Nao reconhecido"
    return [inicio, ack, fim, s["duracao_fmt"]]


def _texto_narrativo(r):
    partes = [
        f'No periodo analisado, o alarme atuou <b>{r["qtd_atuacoes"]}</b> vez(es), '
        f'permanecendo atuado por um total de <b>{r["tempo_total_atuado_fmt"]}</b>.'
    ]
    if r["qtd_retornou_sozinho"]:
        partes.append(
            f'Em <b>{r["qtd_retornou_sozinho"]}</b> ocorrencia(s) o alarme retornou ao '
            f'normal sem reconhecimento do operador.'
        )
    if r["qtd_com_tempo_reconhecimento"]:
        partes.append(
            f'O tempo medio ate o reconhecimento foi de '
            f'<b>{r["tempo_medio_reconhecimento_fmt"]}</b>.'
        )
    if r["qtd_ainda_ativo"]:
        partes.append("Este alarme permanece atuado no momento do fechamento do periodo analisado.")
    return " ".join(partes)


def gerar(caminho_saida, resumo_alarmes, sessoes_alarmes, periodo_texto):
    doc = pdf_comum.novo_documento(caminho_saida)
    story = []

    total_tags = len(resumo_alarmes)
    total_atuacoes = sum(r["qtd_atuacoes"] for r in resumo_alarmes)
    total_sozinho = sum(r["qtd_retornou_sozinho"] for r in resumo_alarmes)
    total_reconhecidas = sum(r["qtd_reconhecidas"] for r in resumo_alarmes)
    total_ainda_ativo = sum(r["qtd_ainda_ativo"] for r in resumo_alarmes)
    tempo_total_geral = sum(r["tempo_total_atuado_s"] for r in resumo_alarmes)

    pdf_comum.cabecalho(
        story, "Relatorio de Alarmes", periodo_texto,
        "Este relatorio resume a atuacao dos alarmes registrados no periodo, "
        "indicando quantas vezes cada alarme atuou, se retornou sozinho ou foi "
        "reconhecido pelo operador, e o tempo total que permaneceu atuado."
    )

    story.append(pdf_comum.tabela_kpis([
        ("Tags de alarme distintas", str(total_tags)),
        ("Total de atuacoes", str(total_atuacoes)),
        ("Retornaram sozinhos (sem reconhecimento)", str(total_sozinho)),
        ("Reconhecidas pelo operador", str(total_reconhecidas)),
        ("Ainda atuados ao final do periodo", str(total_ainda_ativo)),
        ("Tempo total atuado (soma de todos os alarmes)", formatar_duracao(tempo_total_geral)),
    ]))
    story.append(Spacer(1, 14))

    status = classificar_alarmes.contagem_status(sessoes_alarmes)
    story.append(Paragraph("Panorama - status das atuacoes", pdf_comum.styles["SecaoTitulo"]))
    story.append(pdf_graficos.grafico_pizza(
        ["Reconhecido e retornou", "Retornou sozinho", "Ainda ativo"],
        [status["reconhecidos"], status["sozinho"], status["ainda_ativo"]],
        [pdf_graficos.COR_RECONHECIDO, pdf_graficos.COR_SOZINHO, pdf_graficos.COR_ATIVO],
    ))
    story.append(Spacer(1, 10))

    resumo_ordenado = sorted(resumo_alarmes, key=lambda r: -r["tempo_total_atuado_s"])
    top = resumo_ordenado[:TOP_N]
    top_grafico = resumo_ordenado[:TOP_N_GRAFICO]

    story.append(Paragraph(
        f"Top {len(top_grafico)} alarmes por tempo total atuado",
        pdf_comum.styles["SecaoTitulo"],
    ))
    story.append(pdf_graficos.grafico_barras_horizontais(
        [_tag_curta(r["tag"]) for r in reversed(top_grafico)],
        [r["tempo_total_atuado_s"] / 3600 for r in reversed(top_grafico)],
        rotulo_fmt="%.0fh",
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        f"Ranking - Top {len(top)} alarmes por tempo total atuado",
        pdf_comum.styles["SecaoTitulo"],
    ))
    linhas_ranking = [
        [r["tag"], r["descricao"][:38], str(r["qtd_atuacoes"]),
         str(r["qtd_retornou_sozinho"]), r["tempo_total_atuado_fmt"]]
        for r in top
    ]
    story.append(pdf_comum.tabela_ranking(
        ["Tag", "Descricao", "Atuacoes", "Retornou sozinho", "Tempo total"],
        linhas_ranking,
        [3.3 * cm, 7.2 * cm, 2.1 * cm, 2.8 * cm, 2.6 * cm],
    ))

    story.append(PageBreak())
    por_tag = _sessoes_por_tag(sessoes_alarmes)
    for r in top:
        sessoes_tag = por_tag.get(r["tag"], [])
        linhas = [_linha_sessao(s) for s in sessoes_tag]
        idx_ativos = [i for i, s in enumerate(sessoes_tag) if s["status"] == "ATIVO (em aberto)"]
        tabela = pdf_comum.tabela_sessoes(
            ["Atuou em", "Reconhecido em", "Retornou em", "Duracao"],
            linhas,
            [3.6 * cm, 3.6 * cm, 3.6 * cm, 3.6 * cm],
            linhas_ativas=idx_ativos,
        )
        nota = None
        if r["qtd_ainda_ativo"]:
            nota = pdf_comum.nota_box(
                "Atencao", "Este alarme permanece atuado ao final do periodo analisado."
            )
        pdf_comum.secao_tag(story, r["tag"], r["descricao"], _texto_narrativo(r), tabela, nota)

    doc.build(story)
