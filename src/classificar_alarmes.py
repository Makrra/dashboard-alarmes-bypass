"""
Classificacao de Alarmes a partir dos eventos ja carregados por parser_alg.

Um alarme, no canal discreto (Origem = DSC) do InTouch, segue o ciclo:
    UNACK    -> alarme atuou, ainda nao reconhecido (abre sessao)
    ACK      -> operador reconheceu o alarme (ainda atuado)
    ACK_RTN  -> alarme retornou ao normal, ja estava reconhecido (fecha sessao)

Se o alarme retornar ao normal sem nunca aparecer um ACK entre a abertura e o
fechamento da sessao, consideramos que ele "retornou sozinho" (sem
reconhecimento do operador).

Tags de bypass (contendo "_BYP_"), override ("_OV0_"/"_OV1_") e comando
("_CMD_"/prefixo "CMD") sao excluidas daqui porque sao tratadas
separadamente (classificar_bypass.py, classificar_override.py e a aba de
Eventos) - no InTouch, o status dessas tags tambem eh modelado como um
alarme discreto (UNACK/ACK/ACK_RTN), entao precisamos escolher um unico
classificador para cada tag.
"""

import re

from sessoes import rastrear_sessoes, duracao_segundos, formatar_duracao


SINAL_POR_TIPO = {"UNACK": "ON", "ACK": "ACK", "ACK_RTN": "OFF"}

TAG_OVERRIDE = re.compile(r"_OV\d_", re.IGNORECASE)


def eh_evento_de_alarme(e):
    if e["origem"] != "DSC":
        return False
    if e["tipo_evento"] not in SINAL_POR_TIPO:
        return False
    tag = e["tag"].upper()
    if "_BYP_" in tag or tag.endswith("_BYPASS"):
        return False
    if TAG_OVERRIDE.search(tag):
        return False
    if "_CMD_" in tag or tag.startswith("CMD"):
        return False
    return True


def classificar(eventos, dt_fim_periodo):
    """Retorna (sessoes, resumo_por_tag, descricoes)."""
    eventos_alarme = [e for e in eventos if eh_evento_de_alarme(e)]

    descricoes = {}
    for e in eventos_alarme:
        if e["descricao"] and e["tag"] not in descricoes:
            descricoes[e["tag"]] = e["descricao"]

    sessoes = rastrear_sessoes(
        eventos_alarme,
        chave_fn=lambda e: e["tag"],
        sinal_fn=lambda e: SINAL_POR_TIPO.get(e["tipo_evento"]),
        dt_fim_periodo=dt_fim_periodo,
    )

    for s in sessoes:
        s["descricao"] = descricoes.get(s["chave"], s["chave"])
        s["duracao_s"] = duracao_segundos(s, dt_fim_periodo)
        s["duracao_fmt"] = formatar_duracao(s["duracao_s"])
        s["retornou_sozinho"] = s["ack_em"] is None
        s["tempo_reconhecimento_s"] = (
            (s["ack_em"] - s["inicio"]).total_seconds() if s["ack_em"] else None
        )

    resumo = {}
    for s in sessoes:
        tag = s["chave"]
        r = resumo.setdefault(tag, {
            "tag": tag,
            "descricao": s["descricao"],
            "qtd_atuacoes": 0,
            "qtd_retornou_sozinho": 0,
            "qtd_reconhecidas": 0,
            "qtd_ainda_ativo": 0,
            "tempo_total_atuado_s": 0.0,
            "somatorio_tempo_reconhecimento_s": 0.0,
            "qtd_com_tempo_reconhecimento": 0,
        })
        r["qtd_atuacoes"] += 1
        r["tempo_total_atuado_s"] += s["duracao_s"]
        if s["status"] == "ATIVO (em aberto)":
            r["qtd_ainda_ativo"] += 1
        if s["retornou_sozinho"]:
            r["qtd_retornou_sozinho"] += 1
        else:
            r["qtd_reconhecidas"] += 1
        if s["tempo_reconhecimento_s"] is not None:
            r["somatorio_tempo_reconhecimento_s"] += s["tempo_reconhecimento_s"]
            r["qtd_com_tempo_reconhecimento"] += 1

    for r in resumo.values():
        r["tempo_total_atuado_fmt"] = formatar_duracao(r["tempo_total_atuado_s"])
        if r["qtd_com_tempo_reconhecimento"]:
            r["tempo_medio_reconhecimento_s"] = (
                r["somatorio_tempo_reconhecimento_s"] / r["qtd_com_tempo_reconhecimento"]
            )
        else:
            r["tempo_medio_reconhecimento_s"] = None
        r["tempo_medio_reconhecimento_fmt"] = (
            formatar_duracao(r["tempo_medio_reconhecimento_s"])
            if r["tempo_medio_reconhecimento_s"] is not None else "-"
        )

    return sessoes, list(resumo.values()), descricoes


def contagem_status(sessoes):
    """Classificacao mutuamente exclusiva de cada instancia de alarme, para
    graficos de pizza/distribuicao: Reconhecido e encerrado / Retornou
    sozinho (sem reconhecimento) / Ainda ativo (em aberto)."""
    ainda_ativo = sum(1 for s in sessoes if s["status"] == "ATIVO (em aberto)")
    encerrados = [s for s in sessoes if s["status"] != "ATIVO (em aberto)"]
    reconhecidos = sum(1 for s in encerrados if s["ack_em"] is not None)
    sozinho = sum(1 for s in encerrados if s["ack_em"] is None)
    return {"reconhecidos": reconhecidos, "sozinho": sozinho, "ainda_ativo": ainda_ativo}


def contagem_por_dia(sessoes):
    """Numero de atuacoes por dia (data de inicio da sessao), para grafico de
    tendencia. Retorna lista ordenada de (data, quantidade)."""
    from collections import Counter
    contagem = Counter(s["inicio"].date() for s in sessoes)
    return sorted(contagem.items())
