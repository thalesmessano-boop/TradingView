# Automação de Análise Gráfica — XAU/USD (TradingView → WhatsApp)

Automação que analisa o gráfico de XAU/USD no TradingView usando **estrutura
de mercado (BOS/CHoCH)**, **rotulagem heurística de ondas** e **filtro de
volume**, exigindo que o **cenário macro** (tendência maior) esteja alinhado
com o **gatilho no micro** (timeframe de entrada) antes de disparar um sinal.
Quando um sinal válido ocorre, o TradingView envia um webhook para um
pequeno servidor que formata a análise (entrada, stop loss, take profit) e
envia automaticamente para o **WhatsApp**.

## Como funciona (visão geral)

```
TradingView (Pine Script)  --alerta/webhook-->  Servidor (Render/FastAPI)  --API-->  WhatsApp
   BOS/CHoCH + Ondas +                              valida segredo
   Volume + Macro x Micro                           formata mensagem
```

- **Sem repintura**: o script só confirma pivôs e dispara alertas no
  fechamento da barra (`alert.freq_once_per_bar_close`).
- **Sem intervalo fixo**: o timeframe do gatilho (micro) e do contexto
  (macro) são inputs configuráveis no próprio indicador — ajuste conforme o
  cenário for ficando mais claro, sem precisar mexer no servidor.
- A "onda" mostrada é uma **heurística** baseada em pivôs (1‑2‑3‑4‑5 / A‑B‑C),
  não uma contagem de Elliott Wave rigorosa. Ela serve como contexto visual;
  quem decide a entrada de fato é o BOS/CHoCH confirmado + volume acima da
  média + alinhamento macro/micro.

Este guia coloca tudo funcionando de ponta a ponta, na ordem certa:
**1)** criar o segredo do webhook → **2)** criar conta WhatsApp (Meta Cloud
API, gratuita) → **3)** publicar o servidor (Render) → **4)** configurar o
indicador e o alerta no TradingView.

## 1. Gere o segredo do webhook

Esse segredo impede que qualquer pessoa que descubra a URL do seu servidor
consiga mandar mensagens falsas para o seu WhatsApp. Gere um valor único, por
exemplo rodando localmente:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

Guarde o resultado — ele vai ser usado em **dois lugares**: na variável
`WEBHOOK_SECRET` do servidor (passo 3) e no input **"Segredo do webhook"** do
indicador (passo 4). Nunca coloque esse valor em arquivos versionados no
Git (o `.env` já está no `.gitignore` por isso).

## 2. Crie a conta do WhatsApp (Meta Cloud API — gratuita)

Usamos a **Meta WhatsApp Cloud API** com o número de teste que a própria
Meta fornece: gratuito, sem cartão de crédito, envia para até 5 números que
você mesmo verificar. (O Twilio também funciona — está implementado como
alternativa — mas o sandbox dele consome um crédito de teste que acaba.)

1. Crie uma conta em https://developers.facebook.com/ (usa seu login do
   Facebook).
2. Vá em **My Apps → Create App** (https://developers.facebook.com/apps/create/)
   → escolha o tipo **Business** → dê um nome (ex.: "XAUUSD Alerts") → crie.
3. No painel do app, procure o produto **WhatsApp** e clique em **Set up**.
4. Você cai na página **WhatsApp → API Setup**, que já mostra:
   - Um **número de teste** (From) pronto pra usar.
   - O campo **Phone number ID** — copie, vai virar `META_PHONE_NUMBER_ID`.
   - Um **Temporary access token** (válido por 24h) — copie, vai virar
     `META_ACCESS_TOKEN` (num passo abaixo trocamos por um token permanente).
5. Em **To**, clique em **Manage phone number list** e adicione **o seu
   número de WhatsApp** (com DDI+DDD). A Meta manda um código de verificação
   pelo WhatsApp — confirme.
6. Ainda nessa página, clique em **Send message** no template de teste
   (`hello_world`) para confirmar que a mensagem chega no seu WhatsApp.

**Gerando um token permanente** (para o servidor rodar sem precisar trocar
o token a cada 24h):

7. Vá em https://business.facebook.com/settings/system-users
8. **Add** → crie um usuário do sistema (System User) com papel **Admin**.
9. Com o usuário criado, **Add Assets** → aba **Apps** → selecione o app
   criado no passo 2 → marque **Full control** → salve.
10. Clique em **Generate New Token** → selecione o app → marque as
    permissões `whatsapp_business_messaging` e `whatsapp_business_management`
    → **Generate Token**. Copie o token exibido (ele só aparece uma vez) —
    esse é o `META_ACCESS_TOKEN` definitivo, não expira em 24h.

**Criando o template da mensagem** (obrigatório para mensagens iniciadas
pelo servidor, como nossos alertas):

11. Vá em https://business.facebook.com/wa/manage/message-templates/
12. **Create Template** → categoria **Utility** → nome, por exemplo
    `sinal_trading` → idioma **Portuguese (BR)**.
13. No corpo (Body), escreva apenas `{{1}}` (um único parâmetro de texto —
    é nele que o servidor injeta a mensagem completa formatada).
14. Envie para aprovação — normalmente aprova em poucos minutos.
15. Guarde: `META_TEMPLATE_NAME=sinal_trading` e `META_TEMPLATE_LANG=pt_BR`.

Ao final você deve ter: `META_PHONE_NUMBER_ID`, `META_ACCESS_TOKEN`
(permanente), `META_TO_NUMBER` (seu número, só dígitos com DDI, ex.
`5511999999999`), `META_TEMPLATE_NAME` e `META_TEMPLATE_LANG`.

## 3. Publique o servidor no Render

O repositório já inclui um `render.yaml` (Blueprint) e um `Dockerfile`
prontos em [`webhook/`](webhook/) — o Render lê esse arquivo e cria o
serviço automaticamente.

1. Crie uma conta em https://render.com (dá pra usar login do GitHub).
2. No painel, clique em **New +** → **Blueprint**.
3. Conecte sua conta GitHub e selecione o repositório
   `thalesmessano-boop/TradingView`.
4. O Render vai detectar o `render.yaml` na raiz e propor o serviço
   **tradingview-xauusd-webhook**. Confirme a criação.
5. Antes (ou logo depois) de concluir, preencha as variáveis de ambiente
   marcadas como secretas:
   - `WEBHOOK_SECRET` → o valor gerado no passo 1.
   - `META_PHONE_NUMBER_ID` → do passo 2.
   - `META_ACCESS_TOKEN` → o token permanente do passo 2.
   - `META_TO_NUMBER` → seu número, do passo 2 (só dígitos com DDI, ex.
     `5511999999999`).
   - `META_TEMPLATE_NAME` → do passo 2 (ex.: `sinal_trading`).
   - (`WHATSAPP_PROVIDER` e `META_TEMPLATE_LANG` já vêm preenchidos no
     `render.yaml`.)
6. Clique em **Apply**/**Deploy**. O primeiro build leva alguns minutos.
7. Quando o serviço ficar com status **Live**, copie a URL pública, algo
   como `https://tradingview-xauusd-webhook.onrender.com`.
8. Confirme que está no ar abrindo no navegador:
   `https://SEU-SERVICO.onrender.com/health` → deve responder
   `{"status":"ok"}`.

> Plano free do Render "dorme" após um tempo sem tráfego e demora alguns
> segundos para acordar na próxima chamada — geralmente sem problema para
> alertas de trading, mas se isso incomodar, migre para um plano pago
> (mesma configuração, só muda o plano no `render.yaml` ou no painel).

### (Alternativa) Rodar na sua própria VPS

Se preferir não usar o Render: o mesmo `webhook/Dockerfile` funciona em
qualquer host com Docker.

```bash
cd webhook
docker build -t tv-webhook .
docker run -d --restart unless-stopped -p 8000:8000 \
  -e WEBHOOK_SECRET=... -e WHATSAPP_PROVIDER=meta \
  -e META_PHONE_NUMBER_ID=... -e META_ACCESS_TOKEN=... \
  -e META_TO_NUMBER=5511999999999 \
  -e META_TEMPLATE_NAME=sinal_trading -e META_TEMPLATE_LANG=pt_BR \
  tv-webhook
```

Depois coloque um proxy reverso com HTTPS na frente (Caddy/Nginx +
Let's Encrypt), pois o TradingView exige URL pública HTTPS.

## 4. Configure o indicador e o alerta no TradingView

**Indicador** — arquivo [`pine/xauusd_macro_micro_smc.pine`](pine/xauusd_macro_micro_smc.pine):

1. Abra o gráfico de **XAU/USD** no TradingView, no timeframe que você quer
   usar como **gatilho de entrada** (ex.: 15m ou 1H).
2. Pine Editor → cole o conteúdo do arquivo → **Add to chart**.
3. Nos inputs do indicador, configure:
   - **Timeframe macro**: o timeframe da tendência maior que precisa estar
     alinhada (ex.: `240` para 4H, ou `D` para diário).
   - **Sensibilidade dos pivôs** (macro/micro): quantas barras de cada lado
     confirmam um topo/fundo. Valores maiores = estrutura mais "limpa",
     porém com mais atraso na confirmação.
   - **Volume mínimo x média**: filtro para só considerar rompimentos com
     volume relevante.
   - **ATR / Buffer do Stop / R:R**: como o stop loss e o take profit são
     calculados a partir do swing rompido.
   - **Segredo do webhook**: cole o **mesmo valor** gerado no passo 1 e já
     configurado no Render como `WEBHOOK_SECRET`.

**Alerta:**

1. Com o indicador no gráfico, clique em **Criar Alerta** (ícone de
   relógio).
2. Em **Condição**, selecione o indicador → **"Any alert() function call"**
   (é essa opção que usa o payload JSON dinâmico gerado pelo script).
3. Em **Ações do Alerta**, marque **Webhook URL** e informe a URL do Render
   do passo 3, com o caminho `/webhook/tradingview`, por exemplo:
   `https://tradingview-xauusd-webhook.onrender.com/webhook/tradingview`
4. Deixe **Expiração** em "Aberto" (sem data de expiração) para rodar de
   forma contínua.
5. O campo "Mensagem" pode ficar com o padrão — o conteúdo enviado é o JSON
   definido dentro do `alert()` no Pine Script.

Pronto — a partir daqui, todo BOS/CHoCH confirmado com volume e alinhamento
macro/micro chega automaticamente no seu WhatsApp com entrada, stop loss e
take profit.

## Testando sem esperar o mercado

Para validar o servidor (local ou já publicado) sem depender de um sinal
real do TradingView:

```bash
cd webhook
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # preencha com seus valores
python server.py       # ou aponte PORT/URL para o serviço no Render
python simulate_alert.py
```

Isso deve chegar no seu WhatsApp uma mensagem como:

```
📊 Sinal XAU/USD - BOS
🟢 COMPRA

Ativo: OANDA:XAUUSD
Timeframe entrada: 15 | Macro: 240
Tendência macro/micro: ALTA (alinhadas)
Onda (heurística): 3
Volume: 1.80x a média

➡️ Entrada: 2415.30
🛑 Stop Loss: 2408.50
🎯 Take Profit: 2428.90
R:R: 2.0 | Risco sugerido: 1.0%
```

### Testes automatizados

O servidor tem testes cobrindo validação do segredo, payload inválido,
formatação da mensagem e tratamento de falha de envio:

```bash
cd webhook
pip install -r requirements-dev.txt
python -m pytest -q
```

Eles também rodam automaticamente via GitHub Actions
(`.github/workflows/webhook-tests.yml`) a cada push/PR que toque em
`webhook/`.

## Ajustando o alinhamento macro/micro

Como combinado, não há um cronograma fixo — os dois timeframes (macro e
micro) são inputs do indicador. Comece com uma combinação como **4H (macro)
+ 15m (micro)** ou **D (macro) + 1H (micro)** e ajuste a sensibilidade dos
pivôs e o multiplicador de volume observando os sinais gerados. Qualquer
ajuste é feito direto nos inputs do Pine Script, sem precisar tocar no
servidor.

## Próximos passos possíveis

- Registrar os sinais enviados em um banco de dados/planilha para
  acompanhar performance.
- Adicionar deduplicação (evitar reenviar o mesmo sinal em caso de retry do
  TradingView).
- Usar a skill `elliott-wyckoff-wave-analysis` para complementar
  periodicamente os sinais automáticos com uma leitura manual/IA de Elliott
  Wave e zonas de Wyckoff.
