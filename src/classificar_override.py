"""
Classificacao de Override a partir dos eventos ja carregados por parser_alg.

Uma tag de override tem "_OV0_" ou "_OV1_" no nome e aparece em pares, no
mesmo padrao de bypass (ver classificar_bypass.py):
    <base>_W  -> comando/confirmacao do operador (Origem=OPR ou DDE, Tipo_Evento=EVT)
    <base>_R  -> status/alarme de override (Origem=DSC, Tipo_Evento=UNACK/ACK/ACK_RTN)

Preferimos o sinal da tag _W (contem o operador que efetivamente comandou a
mudanca). Se uma tag-base nao tiver eventos _W no periodo, caimos no
fallback pela tag _R: UNACK = ativacao, ACK_RTN = remocao.
"""

import re
from collections import defaultdict

from sessoes import sessoes_de_sinais, duracao_segundos, formatar_duracao


ESTADOS_ATIVO = {"em override", "em over-ride"}
ESTADOS_INATIVO = {"fora de override", "fora de overrid", "sem override", "sem over-ride"}

TAG_OVERRIDE = re.compile(r"_OV\d_", re.IGNORECASE)


def _tag_base(tag):
    if tag.upper().endswith("_W") or tag.upper().endswith("_R"):
        return tag[:-2]
    return tag


def eh_evento_de_override(e):
    return bool(TAG_OVERRIDE.search(e["tag"].upper()))


def sinal_evento_w(e):
    novo = e["estado_novo"].strip().lower()
    anterior = e["estado_anterior"].strip().lower()
    if novo in ESTADOS_ATIVO and anterior in ESTADOS_INATIVO:
        return "ON"
    if novo in ESTADOS_INATIVO and anterior in ESTADOS_ATIVO:
        return "OFF"
    return None


def classificar(eventos, dt_fim_periodo):
    """Retorna (sessoes, resumo_por_tag)."""
    eventos_override = [e for e in eventos if eh_evento_de_override(e)]

    por_base = defaultdict(list)
    descricoes = {}
    for e in eventos_override:
        base = _tag_base(e["tag"])
        por_base[base].append(e)
        if e["descricao"] and (e["tag"].upper().endswith("_R") or base not in descricoes):
            descricoes[base] = e["descricao"]

    sessoes = []
    for base, evts in por_base.items():
        evts_w = [e for e in evts if e["tag"].upper().endswith("_W") and e["tipo_evento"] == "EVT"]
        evts_r = [e for e in evts if e["tag"].upper().endswith("_R")]

        sinais = []
        for e in evts_w:
            sinal = sinal_evento_w(e)
            if sinal:
                sinais.append((e["dt"], sinal, e["operador"]))

        if not sinais:
            for e in evts_r:
                if e["tipo_evento"] == "UNACK":
                    sinais.append((e["dt"], "ON", e["operador"]))
                elif e["tipo_evento"] == "ACK_RTN":
                    sinais.append((e["dt"], "OFF", e["operador"]))

        for sessao in sessoes_de_sinais(sinais):
            sessao["chave"] = base
            sessao["descricao"] = descricoes.get(base, base)
            sessao["duracao_s"] = duracao_segundos(sessao, dt_fim_periodo)
            sessao["duracao_fmt"] = formatar_duracao(sessao["duracao_s"])
            sessoes.append(sessao)

    resumo = {}
    for s in sessoes:
        tag = s["chave"]
        r = resumo.setdefault(tag, {
            "tag": tag,
            "descricao": s["descricao"],
            "qtd_ativacoes": 0,
            "qtd_ainda_ativo": 0,
            "tempo_total_override_s": 0.0,
            "operadores": defaultdict(int),
        })
        r["qtd_ativacoes"] += 1
        r["tempo_total_override_s"] += s["duracao_s"]
        if s["status"] == "ATIVO (em aberto)":
            r["qtd_ainda_ativo"] += 1
        if s["operador_abertura"]:
            r["operadores"][s["operador_abertura"]] += 1

    for r in resumo.values():
        r["tempo_total_override_fmt"] = formatar_duracao(r["tempo_total_override_s"])
        r["operadores_resumo"] = ", ".join(
            f"{op} ({n}x)" for op, n in sorted(r["operadores"].items(), key=lambda kv: -kv[1])
        )

    return sessoes, list(resumo.values())


def contagem_por_operador(sessoes):
    """Numero de ativacoes de override por operador, ordenado do que mais
    ativou para o que menos ativou."""
    contagem = defaultdict(int)
    for s in sessoes:
        if s["operador_abertura"]:
            contagem[s["operador_abertura"]] += 1
    return sorted(contagem.items(), key=lambda kv: -kv[1])
