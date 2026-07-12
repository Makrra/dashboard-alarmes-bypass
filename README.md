# Análise de Alarmes, Eventos e Bypass

Ferramenta que lê os arquivos `.ALG` exportados do SCADA (InTouch/Wonderware) e
gera automaticamente:

- Um **Excel** com a linha do tempo de todos os alarmes/bypass e resumos agregados por tag.
- Um **PDF de Alarmes**: quantas vezes cada alarme atuou, se retornou sozinho ou foi
  reconhecido, e quanto tempo ficou atuado.
- Um **PDF de Bypass**: quando cada bypass foi ativado, por qual operador, quando
  foi retirado e quanto tempo ficou ativo.

## Como usar (operador)

1. Dê duplo clique em `dist\AnaliseAlarmesBypass.exe`.
2. Quando pedir o caminho da pasta, arraste a pasta com os arquivos `.ALG`
   (pode ter subpastas, tipo `000_Dados Analise\2026\Janeiro\`) para dentro
   da janela preta e aperte ENTER.
3. Aguarde a mensagem "Concluido!". Os 3 arquivos ficam salvos numa subpasta
   chamada `Relatorios` dentro da pasta que você informou.
4. Se aparecer algum erro, tire um print da tela antes de fechar.

## Como gerar o executável (desenvolvedor)

Pré-requisitos: Python 3.10+ instalado.

```bat
build.bat
```

Isso instala as dependências (`requirements.txt`) e gera
`dist\AnaliseAlarmesBypass.exe` (arquivo único, não precisa instalar Python na
máquina que for usar o `.exe`).

## Estrutura do código (`src/`)

- `parser_alg.py` — leitura dos `.ALG` (encoding CP1252, recursivo em pastas).
- `sessoes.py` — motor genérico de máquina de estados (ativo/inativo/reconhecido),
  reaproveitado tanto para alarmes quanto para bypass.
- `classificar_alarmes.py` / `classificar_bypass.py` — regras específicas de
  cada tipo, usando o motor de `sessoes.py`.
- `relatorio_excel.py` — gera o `.xlsx` (openpyxl).
- `relatorio_pdf_alarmes.py` / `relatorio_pdf_bypass.py` / `pdf_comum.py` —
  geram os PDFs didáticos (reportlab).
- `main.py` — ponto de entrada (linha de comando).
- `organizar_dados.py` — organiza `.ALG` soltos em `000_Dados Analise/<AAAA>/<Mês>/`
  a partir da data codificada no nome do arquivo (`AAMMDDHH.ALG`). Idempotente.
- `enviar_firebase.py` / `gerenciar_usuarios_firebase.py` — ver seção do painel online abaixo.

## Painel online (Firebase + GitHub Pages)

Além dos relatórios locais, os dados processados (sessões + resumos, nunca os
`.ALG` brutos) podem ser enviados mensalmente para o Firestore e
visualizados/filtrados numa página com login, publicada por este mesmo
repositório via GitHub Pages (`index.html` na raiz). Só usuários autenticados
**e** presentes na coleção `usuarios_permitidos` conseguem ler os dados — o
repositório é público, mas os dados não.

### Configuração inicial (uma vez só)

1. No [Firebase Console](https://console.firebase.google.com), crie um
   projeto (plano Spark/gratuito).
2. Habilite **Firestore Database** (modo nativo).
3. Habilite **Authentication > Sign-in method > E-mail/senha**.
4. Em **Configurações do projeto > Seus apps**, adicione um app Web e copie
   o objeto `firebaseConfig` — cole no início do `<script>` em `index.html`
   (não é segredo, pode ficar público).
5. Em **Configurações do projeto > Contas de serviço**, gere uma chave
   privada (JSON), salve em `credenciais/firebase-service-account.json`
   (já está no `.gitignore`, nunca é commitada).
6. Cole o conteúdo de `firestore.rules` em **Firestore Database > Regras >
   Publicar**.
7. Ative o **GitHub Pages** deste repositório (Settings > Pages).

### Organizar arquivos novos

Se `.ALG` novos forem jogados soltos em `000_Dados Analise/`, rode primeiro:

```bat
python src/organizar_dados.py "000_Dados Analise"
```

Isso os move para `000_Dados Analise/<AAAA>/<Mês>/` com base na data no nome
do arquivo. Não move arquivos com nome fora do padrão (reporta no final).

### Enviar dados

```bat
python src/enviar_firebase.py "000_Dados Analise"
```

Aponte sempre para a pasta **raiz de todos os dados** (não um ano/mês
específico), para que sessões que ficaram em aberto num período fechem
corretamente quando reaparecem nos dados seguintes. O envio é idempotente —
rodar de novo não duplica nada.

**Cota gratuita do Firestore**: o plano Spark permite só 20 mil escritas por
dia. Uma carga inicial grande (vários anos de uma vez) pode passar disso —
use `--apenas-meses AAAA` (ou `AAAA-MM`) para restringir o que é gravado
nesta execução sem afetar a reclassificação (que sempre usa o histórico
completo), e rode o restante em outro dia:

```bat
python src/enviar_firebase.py "000_Dados Analise" --apenas-meses 2025
python src/enviar_firebase.py "000_Dados Analise" --apenas-meses 2026
```

### Gestão de usuários do painel

O painel tem autocadastro com aprovação manual (ver `index.html` — tela de
cadastro + botão "Aprovações", visível só para o admin). Também dá pra
gerenciar por linha de comando:

```bat
python src/gerenciar_usuarios_firebase.py listar-pendentes
python src/gerenciar_usuarios_firebase.py aprovar email@exemplo.com
python src/gerenciar_usuarios_firebase.py rejeitar email@exemplo.com
python src/gerenciar_usuarios_firebase.py adicionar email@exemplo.com "senha-temporaria" "Nome Sobrenome"
python src/gerenciar_usuarios_firebase.py remover email@exemplo.com
python src/gerenciar_usuarios_firebase.py listar
```

## Observações sobre os dados

- Datas/tags "ATIVO (em aberto)" com durações muito longas (centenas de dias)
  normalmente indicam uma tag que parou de gerar eventos no meio do período
  (reconfiguração ou desativação no SCADA), não necessariamente um alarme ou
  bypass fisicamente atuado o tempo todo — vale conferir a tag no SCADA se
  aparecer um valor assim.
- O relatório PDF traz apenas os 15 alarmes/bypass com maior tempo total; o
  detalhe completo de todas as tags fica no Excel (abas "Resumo Alarmes" e
  "Resumo Bypass").
