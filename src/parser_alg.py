"""
Leitura de arquivos .ALG (log de alarmes/eventos do SCADA InTouch/Wonderware).

Formato de cada linha (separada por ';', encoding CP1252):

    Data;Hora.ms;Tipo_Evento;Origem;Operador;Prioridade;Descricao;Tag;Grupo;Estado_Novo;Estado_Anterior;[Sufixo]

Tipo_Evento: EVT (mudanca de valor; Origem = DDE/LGC/OPR/SYST)
             UNACK / ACK / ACK_RTN (ciclo de reconhecimento do canal discreto; Origem = DSC)

Estado_Novo / Estado_Anterior: partes[9] eh o valor apos o evento, partes[10] eh o
valor anterior. (Confirmado comparando a ordem cronologica das transicoes nos
arquivos de exemplo - a rotulagem usada nos scripts antigos do projeto irmao
estava invertida.)
"""

import os
from datetime import datetime


CAMPOS_MINIMOS = 11


def parse_linha(linha):
    """Parseia uma linha do .ALG. Retorna None se a linha nao for um registro valido."""
    linha = linha.strip()
    if not linha or linha.startswith("Query"):
        return None
    if "\t" in linha:
        linha = linha.split("\t", 1)[1]

    partes = linha.split(";")
    if len(partes) < CAMPOS_MINIMOS:
        return None

    data = partes[0].strip()
    hora = partes[1].strip()
    try:
        dt = datetime.strptime(f"{data} {hora.split('.')[0]}", "%d %b %Y %H:%M:%S")
    except ValueError:
        return None

    return {
        "dt": dt,
        "data": data,
        "hora": hora,
        "tipo_evento": partes[2].strip(),
        "origem": partes[3].strip(),
        "operador": partes[4].strip(),
        "prioridade": partes[5].strip(),
        "descricao": partes[6].strip(),
        "tag": partes[7].strip(),
        "grupo": partes[8].strip(),
        "estado_novo": partes[9].strip(),
        "estado_anterior": partes[10].strip(),
        "sufixo": partes[11].strip() if len(partes) > 11 else "",
    }


def carregar_pasta(caminho_raiz):
    """Varre recursivamente a pasta em busca de arquivos .ALG e devolve todos os
    eventos ordenados por data/hora. Isso garante que sessoes (bypass/alarme) que
    atravessam a virada de arquivo ou de mes sejam tratadas corretamente."""
    eventos = []
    arquivos_lidos = []

    for pasta_atual, _subpastas, arquivos in os.walk(caminho_raiz):
        for nome in sorted(arquivos):
            if not nome.upper().endswith(".ALG"):
                continue
            caminho = os.path.join(pasta_atual, nome)
            arquivos_lidos.append(caminho)
            with open(caminho, encoding="cp1252", errors="replace") as f:
                for linha in f:
                    registro = parse_linha(linha)
                    if registro:
                        registro["arquivo"] = nome
                        eventos.append(registro)

    eventos.sort(key=lambda e: e["dt"])
    return eventos, arquivos_lidos
