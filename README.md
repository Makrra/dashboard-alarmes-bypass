# Painel de Alarmes & Bypass

Página estática (sem build step) que exibe, com login e filtros, as sessões e
resumos de Alarmes/Bypass processados a partir dos `.ALG` do SCADA e
enviados mensalmente ao Firestore pelo projeto
[gestão-alarmes-eventos-bypasses](../gestão-alarmes-eventos-bypasses).

## Como funciona

- `index.html` — tudo em um arquivo só (HTML+CSS+JS), sem framework. Usa o
  SDK do Firebase via CDN (compat build) para autenticação (Email/Senha) e
  leitura no Firestore.
- `firestore.rules` — cópia versionada das Security Rules aplicadas no
  Console do Firebase (o deploy é manual, colando no Console; ver abaixo).

Só usuários autenticados **e** presentes na coleção `usuarios_permitidos`
conseguem ler os dados — o repositório é público, mas os dados não.

## Configuração inicial (uma vez só)

1. No [Firebase Console](https://console.firebase.google.com), crie um
   projeto (plano Spark/gratuito).
2. Habilite **Firestore Database** (modo nativo).
3. Habilite **Authentication > Sign-in method > E-mail/senha**.
4. Em **Configurações do projeto > Seus apps**, adicione um app Web e copie
   o objeto `firebaseConfig` — cole no início do `<script>` em `index.html`
   (não é segredo, pode ficar público).
5. Em **Configurações do projeto > Contas de serviço**, gere uma chave
   privada (JSON) — usada pelos scripts Python de upload/gestão de usuários
   do projeto `gestão-alarmes-eventos-bypasses` (nunca deve ser commitada).
6. Cole o conteúdo de `firestore.rules` em **Firestore Database > Regras >
   Publicar**.
7. Ative o **GitHub Pages** deste repositório (Settings > Pages).

## Adicionar/remover usuário

Não existe autocadastro na página. Use os scripts do projeto principal:

```
python src/gerenciar_usuarios_firebase.py adicionar email@exemplo.com "senha-temporaria" "Nome Sobrenome"
python src/gerenciar_usuarios_firebase.py remover email@exemplo.com
python src/gerenciar_usuarios_firebase.py listar
```

## Enviar dados do mês

No projeto `gestão-alarmes-eventos-bypasses`:

```
python src/enviar_firebase.py "C:\...\2026"
```

Aponte sempre para a pasta do **ano inteiro** (não só o mês novo), para que
sessões que ficaram em aberto num mês fechem corretamente quando reaparecem
nos dados de um mês seguinte.
