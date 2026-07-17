r"""
Envia sessoes e resumos de Alarmes/Bypass (ja classificados) para o Firestore.

Reaproveita o mesmo pipeline de main.py (parser_alg + classificar_alarmes +
classificar_bypass) sem alterar a logica de classificacao. Rode sempre
apontando para a pasta do ANO INTEIRO (ex: "2026\"), nao so o mes novo, para
que sessoes "ATIVO (em aberto)" que fecham num mes seguinte sejam
reclassificadas corretamente - o script sobrescreve (idempotente) os
documentos existentes, entao rodar de novo com o ano inteiro nao duplica
nada, so atualiza o que mudou.

Uso:
    python src/enviar_firebase.py "C:\...\2026" [--dry-run]
    python src/enviar_firebase.py "000_Dados Analise" --apenas-meses 2025

O plano gratuito (Spark) do Firestore tem cota de 20 mil ESCRITAS por dia.
Uma carga inicial grande (varios anos de uma vez) pode passar disso. Use
--apenas-meses (prefixo de mes_referencia, ex: "2025" ou "2025-06") para
restringir o que e GRAVADO nesta execucao sem afetar a reclassificacao (que
sempre usa o historico completo da pasta informada, para sessoes que
atravessam virada de mes/ano ficarem corretas) - rode de novo em outro dia
(cota reseta a meia-noite, horario do Pacifico) com outro prefixo para
completar o restante.

Credencial (service account) esperada em:
    <raiz do projeto>\credenciais\firebase-service-account.json
ou apontada pela variavel de ambiente FIREBASE_CREDENTIALS.
"""

import argparse
import hashlib
import os
from collections import defaultdict
from zoneinfo import ZoneInfo

from parser_alg import carregar_pasta
import classificar_alarmes
import classificar_bypass
from sessoes import formatar_duracao


RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENCIAL_PADRAO = os.path.join(RAIZ_PROJETO, "credenciais", "firebase-service-account.json")
FUSO_HORARIO = ZoneInfo("America/Recife")
TAMANHO_LOTE = 400  # limite do Firestore por batch e 500 operacoes


def localizar(dt):
    if dt is None:
        return None
    return dt.replace(tzinfo=FUSO_HORARIO)


def id_sessao(tipo, tag, inicio):
    bruto = f"{tipo}|{tag}|{inicio.isoformat()}"
    return hashlib.sha1(bruto.encode("utf-8")).hexdigest()[:24]


def id_resumo(mes_referencia, tag):
    sufixo = hashlib.sha1(tag.encode("utf-8")).hexdigest()[:16]
    return f"{mes_referencia}_{sufixo}"


def montar_doc_sessao_alarme(s):
    return {
        "tag": s["chave"],
        "descricao": s["descricao"],
        "mes_referencia": s["mes_referencia"],
        "inicio": localizar(s["inicio"]),
        "fim": localizar(s["fim"]),
        "operador_abertura": s["operador_abertura"] or None,
        "operador_fechamento": s["operador_fechamento"] or None,
        "ack_em": localizar(s["ack_em"]),
        "operador_ack": s["operador_ack"] or None,
        "status": s["status"],
        "duracao_s": s["duracao_s"],
        "duracao_fmt": s["duracao_fmt"],
        "retornou_sozinho": s["retornou_sozinho"],
        "tempo_reconhecimento_s": s["tempo_reconhecimento_s"],
    }


def montar_doc_sessao_bypass(s):
    return {
        "tag": s["chave"],
        "descricao": s["descricao"],
        "mes_referencia": s["mes_referencia"],
        "inicio": localizar(s["inicio"]),
        "fim": localizar(s["fim"]),
        "operador_abertura": s["operador_abertura"] or None,
        "operador_fechamento": s["operador_fechamento"] or None,
        "status": s["status"],
        "duracao_s": s["duracao_s"],
        "duracao_fmt": s["duracao_fmt"],
    }


def recalcular_resumo_alarme_mensal(sessoes):
    """Mesma agregacao de classificar_alarmes.classificar, mas em buckets
    (mes_referencia, tag) em vez de um total unico para todo o periodo."""
    resumo = {}
    for s in sessoes:
        chave_bucket = (s["mes_referencia"], s["chave"])
        r = resumo.setdefault(chave_bucket, {
            "mes_referencia": s["mes_referencia"],
            "tag": s["chave"],
            "descricao": s["descricao"],
            "qtd_atuacoes": 0,
            "qtd_retornou_sozinho": 0,
            "qtd_reconhecidas": 0,
            "qtd_ainda_ativo": 0,
            "tempo_total_atuado_s": 0.0,
            "_soma_reconhecimento_s": 0.0,
            "_qtd_com_reconhecimento": 0,
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
            r["_soma_reconhecimento_s"] += s["tempo_reconhecimento_s"]
            r["_qtd_com_reconhecimento"] += 1

    for r in resumo.values():
        r["tempo_total_atuado_fmt"] = formatar_duracao(r["tempo_total_atuado_s"])
        if r["_qtd_com_reconhecimento"]:
            tempo_medio = r["_soma_reconhecimento_s"] / r["_qtd_com_reconhecimento"]
        else:
            tempo_medio = None
        r["tempo_medio_reconhecimento_s"] = tempo_medio
        r["tempo_medio_reconhecimento_fmt"] = (
            formatar_duracao(tempo_medio) if tempo_medio is not None else "-"
        )
        del r["_soma_reconhecimento_s"]
        del r["_qtd_com_reconhecimento"]

    return list(resumo.values())


def recalcular_resumo_bypass_mensal(sessoes):
    resumo = {}
    for s in sessoes:
        chave_bucket = (s["mes_referencia"], s["chave"])
        r = resumo.setdefault(chave_bucket, {
            "mes_referencia": s["mes_referencia"],
            "tag": s["chave"],
            "descricao": s["descricao"],
            "qtd_ativacoes": 0,
            "qtd_ainda_ativo": 0,
            "tempo_total_bypass_s": 0.0,
            "_operadores": defaultdict(int),
        })
        r["qtd_ativacoes"] += 1
        r["tempo_total_bypass_s"] += s["duracao_s"]
        if s["status"] == "ATIVO (em aberto)":
            r["qtd_ainda_ativo"] += 1
        if s["operador_abertura"]:
            r["_operadores"][s["operador_abertura"]] += 1

    for r in resumo.values():
        r["tempo_total_bypass_fmt"] = formatar_duracao(r["tempo_total_bypass_s"])
        r["operadores_resumo"] = ", ".join(
            f"{op} ({n}x)" for op, n in sorted(r["_operadores"].items(), key=lambda kv: -kv[1])
        )
        r["operadores"] = dict(r["_operadores"])
        del r["_operadores"]

    return list(resumo.values())


def conectar():
    import firebase_admin
    from firebase_admin import credentials

    caminho = os.environ.get("FIREBASE_CREDENTIALS", CREDENCIAL_PADRAO)
    if not os.path.isfile(caminho):
        raise SystemExit(
            f"Credencial do Firebase nao encontrada em:\n  {caminho}\n\n"
            "Gere em: Firebase Console > Configuracoes do projeto > Contas de "
            "servico > Gerar nova chave privada. Salve o JSON nesse caminho, "
            "ou aponte a variavel de ambiente FIREBASE_CREDENTIALS para outro local."
        )
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(caminho))

    from firebase_admin import firestore
    return firestore.client()


def gravar_em_lotes(db, colecao, docs_por_id):
    itens = list(docs_por_id.items())
    ref_colecao = db.collection(colecao)
    for inicio in range(0, len(itens), TAMANHO_LOTE):
        lote = db.batch()
        for doc_id, dados in itens[inicio:inicio + TAMANHO_LOTE]:
            lote.set(ref_colecao.document(doc_id), dados)
        lote.commit()


def limpar_orfaos(db, colecao, meses_alvo, ids_validos):
    """Remove documentos cujo mes_referencia esteja no escopo desta execucao
    mas que nao fazem mais parte da classificacao atual - acontece quando a
    fronteira/inicio de uma sessao muda entre execucoes (ex: mudanca na
    logica de classificacao, ou reclassificacao com mais historico do que a
    primeira carga tinha), deixando o documento antigo como orfao pra sempre
    (o script so faz set/upsert, nunca apagava sozinho)."""
    apagados = 0
    ref_colecao = db.collection(colecao)
    for mes in meses_alvo:
        existentes = ref_colecao.where("mes_referencia", "==", mes).stream()
        lote = db.batch()
        pendentes = 0
        for doc in existentes:
            if doc.id not in ids_validos:
                lote.delete(doc.reference)
                pendentes += 1
                apagados += 1
                if pendentes >= TAMANHO_LOTE:
                    lote.commit()
                    lote = db.batch()
                    pendentes = 0
        if pendentes:
            lote.commit()
    return apagados


def main():
    parser = argparse.ArgumentParser(
        description="Envia sessoes e resumos de Alarmes/Bypass para o Firestore."
    )
    parser.add_argument(
        "pasta",
        help="Pasta com os .ALG (use a pasta do ANO INTEIRO, ex: '2026', nao so o mes novo)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Apenas mostra as contagens, sem gravar nada no Firestore",
    )
    parser.add_argument(
        "--apenas-meses", default=None, metavar="PREFIXO",
        help="So GRAVA sessoes/resumos cujo mes_referencia comece com esse prefixo "
             "(ex: '2025' ou '2025-06'). A reclassificacao continua usando o "
             "historico completo da pasta informada. Util para nao estourar a "
             "cota diaria gratuita do Firestore em cargas iniciais grandes.",
    )
    args = parser.parse_args()

    print(f"Lendo arquivos .ALG em: {args.pasta}")
    eventos, arquivos = carregar_pasta(args.pasta)
    if not eventos:
        print("Nenhum evento valido foi encontrado nessa pasta.")
        return
    print(f"  {len(arquivos)} arquivo(s) .ALG lido(s), {len(eventos):,} evento(s).")

    dt_fim = eventos[-1]["dt"]
    sessoes_alarmes, _, _ = classificar_alarmes.classificar(eventos, dt_fim)
    sessoes_bypass, _ = classificar_bypass.classificar(eventos, dt_fim)

    for s in sessoes_alarmes:
        s["mes_referencia"] = s["inicio"].strftime("%Y-%m")
    for s in sessoes_bypass:
        s["mes_referencia"] = s["inicio"].strftime("%Y-%m")

    resumo_alarmes = recalcular_resumo_alarme_mensal(sessoes_alarmes)
    resumo_bypass = recalcular_resumo_bypass_mensal(sessoes_bypass)

    meses = sorted(
        {s["mes_referencia"] for s in sessoes_alarmes}
        | {s["mes_referencia"] for s in sessoes_bypass}
    )

    print(f"\n  {len(sessoes_alarmes)} sessao(oes) de alarme.")
    print(f"  {len(sessoes_bypass)} sessao(oes) de bypass.")
    print(f"  {len(resumo_alarmes)} resumo(s) mensal(is) de alarme (mes+tag).")
    print(f"  {len(resumo_bypass)} resumo(s) mensal(is) de bypass (mes+tag).")
    print(f"  Meses cobertos (classificacao completa): {', '.join(meses)}")

    if args.apenas_meses:
        prefixo = args.apenas_meses
        sessoes_alarmes = [s for s in sessoes_alarmes if s["mes_referencia"].startswith(prefixo)]
        sessoes_bypass = [s for s in sessoes_bypass if s["mes_referencia"].startswith(prefixo)]
        resumo_alarmes = [r for r in resumo_alarmes if r["mes_referencia"].startswith(prefixo)]
        resumo_bypass = [r for r in resumo_bypass if r["mes_referencia"].startswith(prefixo)]
        meses = [m for m in meses if m.startswith(prefixo)]
        total_docs = len(sessoes_alarmes) + len(sessoes_bypass) + len(resumo_alarmes) + len(resumo_bypass)
        print(f"\n  --apenas-meses={prefixo}: restrito a {len(meses)} mes(es), {total_docs} documento(s) a gravar.")

    if args.dry_run:
        print("\n--dry-run: nada foi gravado no Firestore.")
        return

    db = conectar()

    docs_sessoes_alarme = {
        id_sessao("alarme", s["chave"], s["inicio"]): montar_doc_sessao_alarme(s)
        for s in sessoes_alarmes
    }
    docs_sessoes_bypass = {
        id_sessao("bypass", s["chave"], s["inicio"]): montar_doc_sessao_bypass(s)
        for s in sessoes_bypass
    }
    docs_resumo_alarme = {
        id_resumo(r["mes_referencia"], r["tag"]): r for r in resumo_alarmes
    }
    docs_resumo_bypass = {
        id_resumo(r["mes_referencia"], r["tag"]): r for r in resumo_bypass
    }

    print("\nGravando no Firestore...")
    gravar_em_lotes(db, "sessoes_alarme", docs_sessoes_alarme)
    print(f"  sessoes_alarme: {len(docs_sessoes_alarme)} documento(s)")
    gravar_em_lotes(db, "sessoes_bypass", docs_sessoes_bypass)
    print(f"  sessoes_bypass: {len(docs_sessoes_bypass)} documento(s)")
    gravar_em_lotes(db, "resumos_alarme", docs_resumo_alarme)
    print(f"  resumos_alarme: {len(docs_resumo_alarme)} documento(s)")
    gravar_em_lotes(db, "resumos_bypass", docs_resumo_bypass)
    print(f"  resumos_bypass: {len(docs_resumo_bypass)} documento(s)")

    print("\nLimpando documentos orfaos (sessoes que mudaram de fronteira entre execucoes)...")
    apagados = 0
    apagados += limpar_orfaos(db, "sessoes_alarme", meses, set(docs_sessoes_alarme.keys()))
    apagados += limpar_orfaos(db, "sessoes_bypass", meses, set(docs_sessoes_bypass.keys()))
    apagados += limpar_orfaos(db, "resumos_alarme", meses, set(docs_resumo_alarme.keys()))
    apagados += limpar_orfaos(db, "resumos_bypass", meses, set(docs_resumo_bypass.keys()))
    print(f"  {apagados} documento(s) orfao(s) removido(s).")

    from firebase_admin import firestore
    db.collection("metadados").document("periodos").set(
        {"meses": firestore.ArrayUnion(meses)}, merge=True
    )
    print(f"  metadados/periodos atualizado com: {', '.join(meses)}")

    print("\nConcluido!")


if __name__ == "__main__":
    main()
