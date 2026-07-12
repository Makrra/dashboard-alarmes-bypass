"""
Ferramenta de Analise de Alarmes, Eventos e Bypass (.ALG)

Pede a pasta onde estao os arquivos .ALG (pode conter subpastas, ex:
2026/Janeiro/*.ALG), consolida tudo e gera:
  - um Excel com a linha do tempo e os resumos agregados;
  - um PDF didatico de Alarmes;
  - um PDF didatico de Bypass.
"""

import os
import sys
import traceback
from datetime import datetime

from parser_alg import carregar_pasta
import classificar_alarmes
import classificar_bypass
import relatorio_excel
import relatorio_pdf_alarmes
import relatorio_pdf_bypass


def limpar_caminho(caminho):
    return caminho.strip().strip('"').strip("'")


def pedir_pasta():
    print("=" * 70)
    print(" Ferramenta de Analise de Alarmes, Eventos e Bypass (.ALG)")
    print("=" * 70)
    print()
    print("Informe o caminho completo da pasta onde estao os arquivos .ALG.")
    print("Dica: pode arrastar a pasta para esta janela e depois apertar ENTER.")
    print()
    while True:
        caminho = limpar_caminho(input("Pasta com os dados: "))
        if not caminho:
            print("Informe um caminho valido.\n")
            continue
        if not os.path.isdir(caminho):
            print(f'A pasta "{caminho}" nao foi encontrada. Tente novamente.\n')
            continue
        return caminho


def main():
    pasta_dados = pedir_pasta()

    print("\nLendo arquivos .ALG (isso pode levar alguns minutos em pastas grandes)...")
    eventos, arquivos = carregar_pasta(pasta_dados)

    if not eventos:
        print("\nNenhum evento valido foi encontrado nessa pasta (verifique se ha")
        print("arquivos .ALG nela ou em subpastas).")
        return

    print(f"  {len(arquivos)} arquivo(s) .ALG lido(s).")
    print(f"  {len(eventos):,} evento(s) processado(s).")

    dt_fim = eventos[-1]["dt"]
    periodo_texto = (
        f'Periodo analisado: {eventos[0]["dt"].strftime("%d/%m/%Y")} '
        f'a {eventos[-1]["dt"].strftime("%d/%m/%Y")}'
    )

    print("\nClassificando alarmes e bypass...")
    sessoes_alarmes, resumo_alarmes, _ = classificar_alarmes.classificar(eventos, dt_fim)
    sessoes_bypass, resumo_bypass = classificar_bypass.classificar(eventos, dt_fim)
    print(f"  {len(resumo_alarmes)} tag(s) de alarme distintas.")
    print(f"  {len(resumo_bypass)} tag(s) de bypass distintas.")

    carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
    pasta_saida = os.path.join(pasta_dados, "Relatorios")
    os.makedirs(pasta_saida, exist_ok=True)

    caminho_excel = os.path.join(pasta_saida, f"Alarmes_e_Bypass_{carimbo}.xlsx")
    caminho_pdf_alarmes = os.path.join(pasta_saida, f"Relatorio_Alarmes_{carimbo}.pdf")
    caminho_pdf_bypass = os.path.join(pasta_saida, f"Relatorio_Bypass_{carimbo}.pdf")

    print("\nGerando relatorios...")
    relatorio_excel.gerar(
        caminho_excel, eventos, resumo_alarmes, resumo_bypass,
        sessoes_alarmes, sessoes_bypass, periodo_texto,
    )
    print(f"  Excel: {caminho_excel}")

    relatorio_pdf_alarmes.gerar(caminho_pdf_alarmes, resumo_alarmes, sessoes_alarmes, periodo_texto)
    print(f"  PDF Alarmes: {caminho_pdf_alarmes}")

    relatorio_pdf_bypass.gerar(caminho_pdf_bypass, resumo_bypass, sessoes_bypass, periodo_texto)
    print(f"  PDF Bypass: {caminho_pdf_bypass}")

    print("\nConcluido! Os arquivos foram salvos em:")
    print(f"  {pasta_saida}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("\nOcorreu um erro inesperado:\n")
        traceback.print_exc()
    finally:
        print()
        try:
            input("Pressione ENTER para sair...")
        except EOFError:
            pass
