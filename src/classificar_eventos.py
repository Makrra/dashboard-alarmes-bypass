"""
Extrai "eventos" (acoes do operador) a partir dos eventos brutos ja
carregados por parser_alg: login no console, reconhecimento de alarmes
(ACK, de qualquer tag) e comandos diretos (tags "_CMD_"/prefixo "CMD").

Diferente de alarme/bypass/override, isso nao eh modelado como sessao
(ativo/inativo) - e uma acao pontual do operador. Por isso agregamos direto
por (mes, operador, acao) em vez de gravar cada ocorrencia bruta (que
chegaria a dezenas de milhares de linhas so nesse recorte).
"""

import re
from collections import defaultdict


TAG_LOGIN = re.compile(r"\\LOGIN$", re.IGNORECASE)
TAG_CMD = re.compile(r"_CMD_|^CMD", re.IGNORECASE)


def identificar_acao(e):
    tag = e["tag"].upper()
    if TAG_LOGIN.search(tag):
        return "Login" if e["tipo_evento"] == "EVT" else None
    if e["tipo_evento"] == "ACK":
        return "Reconhecimento"
    if TAG_CMD.search(tag) and e["tipo_evento"] in ("EVT", "UNACK"):
        return "Comando"
    return None


def classificar(eventos):
    """Retorna a lista de acoes de operador identificadas nos eventos brutos:
    {dt, mes_referencia, acao, operador, tag, descricao}."""
    acoes = []
    for e in eventos:
        operador = (e["operador"] or "").strip()
        if not operador or operador.lower() == "none":
            continue
        acao = identificar_acao(e)
        if acao is None:
            continue
        acoes.append({
            "dt": e["dt"],
            "mes_referencia": e["dt"].strftime("%Y-%m"),
            "acao": acao,
            "operador": operador.lower(),
            "tag": e["tag"],
            "descricao": e["descricao"],
        })
    return acoes


def resumo_mensal(acoes):
    """Agrega por (mes_referencia, operador, acao) -> contagem, pra manter o
    volume de dados enviado ao Firestore pequeno (poucas centenas de docs,
    nao dezenas de milhares)."""
    contagem = defaultdict(int)
    ultima_tag_desc = {}
    for a in acoes:
        chave = (a["mes_referencia"], a["operador"], a["acao"])
        contagem[chave] += 1
        ultima_tag_desc[chave] = (a["tag"], a["descricao"])

    resumo = []
    for (mes, operador, acao), qtd in contagem.items():
        tag, descricao = ultima_tag_desc[(mes, operador, acao)]
        resumo.append({
            "mes_referencia": mes,
            "operador": operador,
            "acao": acao,
            "quantidade": qtd,
            "exemplo_tag": tag,
            "exemplo_descricao": descricao,
        })
    return resumo


def contagem_por_operador(acoes):
    """Total de acoes por operador (todas as categorias somadas), ordenado
    do mais ativo para o menos ativo."""
    contagem = defaultdict(int)
    for a in acoes:
        contagem[a["operador"]] += 1
    return sorted(contagem.items(), key=lambda kv: -kv[1])
