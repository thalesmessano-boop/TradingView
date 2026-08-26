"""
Simula um alerta do TradingView contra o servidor rodando localmente, para
validar a formatação da mensagem e o envio ao WhatsApp sem esperar um sinal
real do mercado.

Uso:
    python server.py            # em um terminal
    python test_local.py        # em outro terminal
"""
import os

import requests
from dotenv import load_dotenv

load_dotenv()

payload = {
    "secret": os.getenv("WEBHOOK_SECRET", "troque-este-segredo"),
    "symbol": "XAUUSD",
    "exchange": "OANDA",
    "side": "BUY",
    "event": "BOS",
    "macro_trend": "BULL",
    "micro_trend": "BULL",
    "timeframe": "15",
    "macro_timeframe": "240",
    "wave_label": "3",
    "volume_ratio": 1.8,
    "entry": 2415.30,
    "stop_loss": 2408.50,
    "take_profit": 2428.90,
    "rr": 2.0,
    "risk_percent": 1.0,
    "time": "2026-08-26T10:15:00Z",
}

port = os.getenv("PORT", "8000")
resp = requests.post(f"http://localhost:{port}/webhook/tradingview", json=payload, timeout=15)
print(resp.status_code, resp.text)
