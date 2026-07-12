r"""
Organiza arquivos .ALG soltos em `000_Dados Analise/<AAAA>/<NomeDoMes>/`, a
partir da data codificada no proprio nome do arquivo (formato do InTouch:
AAMMDDHH.ALG, ex: "26010100.ALG" = 01/01/2026).

Idempotente: um arquivo que ja esta na subpasta correta e ignorado. Nomes
que nao batem com o padrao esperado ficam onde estao (nao move as cegas) e
sao reportados no final para conferencia manual.

Uso:
    python src/organizar_dados.py "000_Dados Analise"
"""

import argparse
import os
import re
import shutil

MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

PADRAO_NOME = re.compile(r"^(\d{2})(\d{2})(\d{2})\d{2}\.ALG$", re.IGNORECASE)


def destino_para(nome_arquivo):
    m = PADRAO_NOME.match(nome_arquivo)
    if not m:
        return None
    aa, mm, _dd = m.groups()
    mes_idx = int(mm)
    if not 1 <= mes_idx <= 12:
        return None
    ano = 2000 + int(aa)
    return str(ano), MESES[mes_idx - 1]


def organizar(pasta_raiz):
    movidos = 0
    ja_organizados = 0
    invalidos = []

    for pasta_atual, subpastas, arquivos in list(os.walk(pasta_raiz)):
        for nome in arquivos:
            if not nome.upper().endswith(".ALG"):
                continue
            destino = destino_para(nome)
            if destino is None:
                invalidos.append(os.path.join(pasta_atual, nome))
                continue

            ano, mes = destino
            pasta_destino = os.path.join(pasta_raiz, ano, mes)
            caminho_origem = os.path.join(pasta_atual, nome)
            caminho_destino = os.path.join(pasta_destino, nome)

            if os.path.abspath(caminho_origem) == os.path.abspath(caminho_destino):
                ja_organizados += 1
                continue

            os.makedirs(pasta_destino, exist_ok=True)
            if os.path.exists(caminho_destino):
                print(f"  AVISO: ja existe {caminho_destino}, mantendo {caminho_origem} onde esta.")
                continue

            shutil.move(caminho_origem, caminho_destino)
            movidos += 1

    return movidos, ja_organizados, invalidos


def main():
    parser = argparse.ArgumentParser(description="Organiza .ALG soltos em pastas Ano/Mes.")
    parser.add_argument("pasta", nargs="?", default="000_Dados Analise")
    args = parser.parse_args()

    print(f"Organizando: {args.pasta}")
    movidos, ja_organizados, invalidos = organizar(args.pasta)

    print(f"\n{movidos} arquivo(s) movido(s).")
    print(f"{ja_organizados} arquivo(s) ja estavam no lugar certo.")
    if invalidos:
        print(f"\n{len(invalidos)} arquivo(s) com nome fora do padrao (nao movidos):")
        for caminho in invalidos:
            print(f"  {caminho}")


if __name__ == "__main__":
    main()
