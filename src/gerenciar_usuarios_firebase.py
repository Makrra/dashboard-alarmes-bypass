r"""
Gestao de usuarios com acesso ao dashboard (Firebase Auth + allowlist
"usuarios_permitidos" no Firestore, usada pelas Security Rules).

Um usuario so consegue LER os dados no dashboard se existir tanto o login
(Firebase Authentication) quanto o documento correspondente em
usuarios_permitidos/{uid} - os dois lados sao criados/removidos juntos por
este script para nao ficarem dessincronizados.

Uso:
    python src/gerenciar_usuarios_firebase.py adicionar email@exemplo.com "senha" "Nome Sobrenome"
    python src/gerenciar_usuarios_firebase.py remover email@exemplo.com
    python src/gerenciar_usuarios_firebase.py listar

Credencial (service account) esperada em:
    <raiz do projeto>\credenciais\firebase-service-account.json
ou apontada pela variavel de ambiente FIREBASE_CREDENTIALS.
"""

import argparse

from enviar_firebase import conectar


def conectar_auth():
    from firebase_admin import auth
    db = conectar()
    return db, auth


def adicionar(email, senha, nome):
    db, auth = conectar_auth()
    usuario = auth.create_user(email=email, password=senha, display_name=nome)
    db.collection("usuarios_permitidos").document(usuario.uid).set({
        "email": email,
        "nome": nome,
    })
    print(f"Usuario criado: {email} (uid={usuario.uid})")
    print("Peca para o usuario trocar a senha no primeiro acesso.")


def remover(email):
    db, auth = conectar_auth()
    usuario = auth.get_user_by_email(email)
    auth.delete_user(usuario.uid)
    db.collection("usuarios_permitidos").document(usuario.uid).delete()
    print(f"Usuario removido: {email} (uid={usuario.uid})")


def listar():
    db, auth = conectar_auth()
    permitidos = {doc.id for doc in db.collection("usuarios_permitidos").stream()}
    print(f"{'Email':40} {'Nome':30} {'Na allowlist?'}")
    for usuario in auth.list_users().iterate_all():
        na_allowlist = "sim" if usuario.uid in permitidos else "NAO (sem acesso de leitura)"
        print(f"{usuario.email or '-':40} {usuario.display_name or '-':30} {na_allowlist}")


def main():
    parser = argparse.ArgumentParser(description="Gestao de usuarios do dashboard (Firebase Auth + allowlist).")
    subparsers = parser.add_subparsers(dest="comando", required=True)

    p_add = subparsers.add_parser("adicionar", help="Cria login + libera acesso de leitura")
    p_add.add_argument("email")
    p_add.add_argument("senha")
    p_add.add_argument("nome")

    p_rem = subparsers.add_parser("remover", help="Remove login e revoga acesso de leitura")
    p_rem.add_argument("email")

    subparsers.add_parser("listar", help="Lista usuarios e se estao na allowlist")

    args = parser.parse_args()

    if args.comando == "adicionar":
        adicionar(args.email, args.senha, args.nome)
    elif args.comando == "remover":
        remover(args.email)
    elif args.comando == "listar":
        listar()


if __name__ == "__main__":
    main()
