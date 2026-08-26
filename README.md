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
TradingView (Pine Script)  --alerta/webhook-->  Servidor (FastAPI)  --API-->  WhatsApp
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

## 1. Indicador Pine Script

Arquivo: [`pine/xauusd_macro_micro_smc.pine`](pine/xauusd_macro_micro_smc.pine)

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
   - **Segredo do webhook**: defina uma string única — ela precisa ser
     **idêntica** ao `WEBHOOK_SECRET` do servidor (passo 3).

## 2. Alerta do TradingView

1. Com o indicador no gráfico, clique em **Criar Alerta** (ícone de
   relógio).
2. Em **Condição**, selecione o indicador → **"Any alert() function call"**
   (é essa opção que usa o payload JSON dinâmico gerado pelo script).
3. Em **Ações do Alerta**, marque **Webhook URL** e informe a URL pública do
   seu servidor, por exemplo:
   `https://SEU-DOMINIO-OU-NGROK/webhook/tradingview`
4. Deixe **Expiração** em "Aberto" (sem data de expiração) para rodar de
   forma contínua.
5. O campo "Mensagem" pode ficar com o padrão — o conteúdo enviado é o JSON
   definido dentro do `alert()` no Pine Script.

> O TradingView exige uma **URL pública HTTPS** para o webhook. Para testar
> localmente antes de colocar em produção, use o [ngrok](https://ngrok.com/)
> (`ngrok http 8000`) para expor seu servidor local temporariamente.

## 3. Servidor de webhook → WhatsApp

Arquivos em [`webhook/`](webhook/).

### Instalação

```bash
cd webhook
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edite `.env`:

- `WEBHOOK_SECRET`: **igual** ao valor colocado no input do Pine Script.
- `WHATSAPP_PROVIDER`: `twilio` (mais simples para uso pessoal) ou `meta`
  (WhatsApp Cloud API oficial da Meta).

**Opção Twilio (recomendada para começar):**
1. Crie uma conta em https://www.twilio.com/whatsapp e ative o **WhatsApp
   Sandbox**.
2. Envie a mensagem de join indicada pelo Twilio para o número sandbox pelo
   seu WhatsApp (necessário uma vez, e o sandbox exige reconexão periódica).
3. Preencha `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`
   (o número do sandbox) e `WHATSAPP_TO` (seu número, no formato
   `whatsapp:+55DDDNUMERO`).
4. Para produção (fora do sandbox), migre para um número Twilio com WhatsApp
   habilitado — mesma configuração, apenas troque `TWILIO_WHATSAPP_FROM`.

**Opção Meta Cloud API:**
1. Crie um app em https://developers.facebook.com/ com o produto **WhatsApp**.
2. Preencha `META_PHONE_NUMBER_ID` e `META_ACCESS_TOKEN`.
3. Como o alerta é uma mensagem **iniciada pelo negócio** (fora da janela de
   24h de atendimento), a Meta exige um **template pré-aprovado**. Crie um
   template simples com um parâmetro de texto e informe o nome em
   `META_TEMPLATE_NAME`.

### Rodando

```bash
python server.py
# ou: uvicorn server:app --host 0.0.0.0 --port 8000
```

Teste sem depender do TradingView:

```bash
python test_local.py
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

### Colocando em produção

O servidor precisa ficar acessível publicamente 24/7 para receber os
webhooks do TradingView. Opções simples: uma VPS pequena, Render, Railway,
Fly.io ou um container Docker em qualquer provedor. Não há Dockerfile neste
repositório ainda — se quiser, posso adicionar um para o provedor que você
escolher.

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
