"""
Motor generico de "sessoes" (ativo/inativo) usado tanto para alarmes quanto
para bypass. Generaliza a maquina de estados validada no script
analise_bypasses.py do projeto irmao: evita contar sinais repetidos (ex:
reconfirmacao do operador ou "piscadas" no restart do SCADA) como novas
sessoes, e registra sessao em aberto quando o periodo analisado termina com
o item ainda ativo.
"""

from collections import defaultdict


def sessoes_de_sinais(sinais):
    """
    Nucleo da maquina de estados, operando sobre uma unica chave (ex: uma tag).

    sinais: lista de tuplas (dt, sinal, operador) com sinal em {"ON","OFF","ACK"},
        em qualquer ordem (sera ordenada por dt).

    Retorna lista de sessoes (sem o campo "chave"):
        {inicio, operador_abertura, fim, operador_fechamento,
         ack_em, operador_ack, status: "Encerrado" | "ATIVO (em aberto)"}
    """
    sinais = sorted(sinais, key=lambda s: s[0])

    estado_atual = "INATIVO"
    dt_abertura = None
    oper_abertura = None
    ack_em = None
    oper_ack = None
    sessoes = []

    for dt, sinal, operador in sinais:
        if sinal == "ON" and estado_atual == "INATIVO":
            estado_atual = "ATIVO"
            dt_abertura = dt
            oper_abertura = operador
            ack_em = None
            oper_ack = None
        elif sinal == "ACK" and estado_atual == "ATIVO" and ack_em is None:
            ack_em = dt
            oper_ack = operador
        elif sinal == "OFF" and estado_atual == "ATIVO":
            sessoes.append({
                "inicio": dt_abertura,
                "operador_abertura": oper_abertura,
                "fim": dt,
                "operador_fechamento": operador,
                "ack_em": ack_em,
                "operador_ack": oper_ack,
                "status": "Encerrado",
            })
            estado_atual = "INATIVO"
            dt_abertura = None
            oper_abertura = None
            ack_em = None
            oper_ack = None
        # ON com estado ja ATIVO = reconfirmacao, ignora.
        # OFF/ACK com estado ja INATIVO = sinal espurio, ignora.

    if estado_atual == "ATIVO" and dt_abertura is not None:
        sessoes.append({
            "inicio": dt_abertura,
            "operador_abertura": oper_abertura,
            "fim": None,
            "operador_fechamento": None,
            "ack_em": ack_em,
            "operador_ack": oper_ack,
            "status": "ATIVO (em aberto)",
        })

    return sessoes


def rastrear_sessoes(eventos, chave_fn, sinal_fn, dt_fim_periodo):
    """
    eventos: lista de dicts (ja carregados por parser_alg), qualquer ordem.
    chave_fn(evento) -> chave de agrupamento (ex: tag, ou tag-base sem sufixo _W/_R).
    sinal_fn(evento) -> "ON", "OFF", "ACK" ou None (ignorado).
    dt_fim_periodo: datetime usado para calcular a duracao de sessoes que
        continuam ativas ao final dos dados (ultimo timestamp encontrado).

    Retorna lista de sessoes, cada uma com "chave" incluida.
    """
    por_chave = defaultdict(list)
    for e in eventos:
        sinal = sinal_fn(e)
        if sinal is not None:
            por_chave[chave_fn(e)].append((e["dt"], sinal, e["operador"]))

    sessoes = []
    for chave, sinais in por_chave.items():
        for sessao in sessoes_de_sinais(sinais):
            sessao["chave"] = chave
            sessoes.append(sessao)

    return sessoes


def duracao_segundos(sessao, dt_fim_periodo):
    fim = sessao["fim"] if sessao["fim"] is not None else dt_fim_periodo
    return (fim - sessao["inicio"]).total_seconds()


def formatar_duracao(segundos):
    if segundos is None or segundos < 0:
        return "?"
    h = int(segundos // 3600)
    m = int((segundos % 3600) // 60)
    s = int(segundos % 60)
    if h >= 48:
        d, hh = divmod(h, 24)
        return f"{d}d {hh:02d}h {m:02d}m"
    return f"{h:02d}h {m:02d}m {s:02d}s"
