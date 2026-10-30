---
name: xau-ops
description: >-
  Operação do pipeline XAU/USD. Mostra os sinais que o webhook recebeu do
  TradingView, o que passou (PASS) e o que foi bloqueado pelo filtro de
  risco (BLOCK) com o motivo, e ajusta os limites (cooldown entre sinais
  repetidos, limite diário, R:R mínimo, distância de stop) em
  webhook/trader/config.json. Use quando o usuário disser "mostra os sinais
  de hoje", "por que foi bloqueado", "ajusta meu risco", "quantos sinais
  hoje", ou para revisar o pipeline de alertas do XAU/USD.
argument-hint: "[log|show|set <chave> <valor>]"
---

# xau-ops

O pipeline XAU/USD roda sozinho, sem ninguém no chat: o indicador Pine
Script dispara o webhook, `webhook/risk.py` decide PASS ou BLOCK, e só um
PASS vira mensagem no WhatsApp. Essa skill é a janela para olhar isso
depois, dentro de uma sessão do Claude Code — ela não manda nada para o
WhatsApp nem para corretora nenhuma, só lê e ajusta os dados que o
servidor já escreveu.

```bash
python3 .claude/skills/xau-ops/ops.py log                    # últimos sinais, PASS e BLOCK
python3 .claude/skills/xau-ops/ops.py log --only block        # só o que foi bloqueado, com o motivo
python3 .claude/skills/xau-ops/ops.py log --limit 50
python3 .claude/skills/xau-ops/ops.py show                    # limites de risco atuais
python3 .claude/skills/xau-ops/ops.py set max_signals_per_day 10
python3 .claude/skills/xau-ops/ops.py set cooldown_minutes 30
```

Rode a partir da raiz do repositório (onde fica a pasta `webhook/`).

## O que ela lê e escreve

| arquivo | o quê |
| --- | --- |
| `webhook/trader/state/risk_log.jsonl` | todo sinal recebido, com o veredito e o motivo de cada BLOCK |
| `webhook/trader/state/alerts_state.json` | sinais recentes, usados para o cooldown e o limite diário |
| `webhook/trader/config.json` | os limites configuráveis (`set` cria/edita este arquivo) |
| `webhook/trader/config.example.json` | os valores padrão, de referência |

## Os limites

| chave | o que controla |
| --- | --- |
| `cooldown_minutes` | tempo mínimo entre dois sinais do mesmo lado+evento+timeframe antes de considerar duplicado |
| `max_signals_per_day` | quantos sinais (PASS) o pipeline deixa passar por dia |
| `min_rr` | R:R mínimo aceito (o Pine Script já filtra por R:R, isso é uma segunda trava) |
| `min_stop_distance_usd` / `max_stop_distance_usd` | faixa aceitável de distância do stop em relação à entrada, em USD |

## Passos

1. Se o usuário perguntar "o que aconteceu hoje" ou similar, rode `log` e
   resuma em poucas linhas: quantos PASS, quantos BLOCK e por quê.
2. Se perguntar por que um sinal específico não chegou no WhatsApp, rode
   `log --only block` e aponte o motivo exato daquele veredito.
3. Para ajustar um limite, confirme o valor novo em uma frase e rode `set`.
   Nunca edite `webhook/trader/config.json` à mão sem o comando — ele
   preserva as outras chaves já salvas.
4. Um limite novo vale a partir do próximo sinal recebido pelo servidor em
   produção (Render); rodar `set` localmente não muda o servidor já
   publicado a menos que `TRADER_DATA_DIR`/o disco sejam os mesmos.

## O que ela nunca faz

Não manda mensagem para o WhatsApp, não chama nenhuma corretora, não
decide entrada/stop/alvo (isso é o indicador Pine Script) e não reduz um
BLOCK a um PASS — só mostra o que já aconteceu e ajusta os limites para o
próximo sinal.

## Aviso

O disco do plano gratuito do Render é efêmero: um redeploy ou um
hibernar/acordar do serviço pode zerar `webhook/trader/state/` (o
histórico e a contagem diária voltam do zero), embora `config.json`
normalmente sobreviva enquanto o mesmo contêiner estiver de pé. Não é
grave — o pipeline continua funcionando, só perde o cooldown acumulado.
