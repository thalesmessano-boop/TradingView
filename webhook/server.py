"""
Servidor que recebe os alertas de webhook do TradingView (indicador
pine/xauusd_macro_micro_smc.pine) e encaminha a análise formatada para o
WhatsApp, com ponto de entrada, stop loss e take profit.
"""
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ValidationError

import risk
from whatsapp import WhatsAppError, send_whatsapp_message

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("tradingview-webhook")

app = FastAPI(title="TradingView XAU/USD Webhook")


class TradingViewAlert(BaseModel):
    secret: str
    symbol: str
    exchange: str | None = None
    side: str  # BUY | SELL
    event: str  # BOS | CHOCH
    macro_trend: str
    micro_trend: str
    timeframe: str
    macro_timeframe: str
    wave_label: str
    volume_ratio: float
    entry: float
    stop_loss: float
    take_profit: float
    rr: float
    risk_percent: float | None = None
    time: str | None = None


SIDE_EMOJI = {"BUY": "🟢 COMPRA", "SELL": "🔴 VENDA"}


def format_message(alert: TradingViewAlert) -> str:
    side_label = SIDE_EMOJI.get(alert.side.upper(), alert.side)
    trend_label = "ALTA" if alert.side.upper() == "BUY" else "BAIXA"
    ativo = f"{alert.exchange}:{alert.symbol}" if alert.exchange else alert.symbol
    return (
        f"📊 *Sinal XAU/USD - {alert.event}*\n"
        f"{side_label}\n\n"
        f"Ativo: {ativo}\n"
        f"Timeframe entrada: {alert.timeframe} | Macro: {alert.macro_timeframe}\n"
        f"Tendência macro/micro: {trend_label} (alinhadas)\n"
        f"Onda (heurística): {alert.wave_label}\n"
        f"Volume: {alert.volume_ratio:.2f}x a média\n\n"
        f"➡️ Entrada: {alert.entry:.2f}\n"
        f"🛑 Stop Loss: {alert.stop_loss:.2f}\n"
        f"🎯 Take Profit: {alert.take_profit:.2f}\n"
        f"R:R: {alert.rr:.1f}"
        + (f" | Risco sugerido: {alert.risk_percent:.1f}%" if alert.risk_percent else "")
        + (f"\nHorário do candle: {alert.time}" if alert.time else "")
        + "\n\n⚠️ Sinal gerado automaticamente. Confirme o contexto antes de operar."
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhook/tradingview")
async def tradingview_webhook(request: Request):
    raw_body = await request.body()
    try:
        alert = TradingViewAlert.model_validate_json(raw_body)
    except ValidationError as exc:
        logger.warning("Payload inválido recebido: %s", exc)
        raise HTTPException(status_code=422, detail="Payload inválido") from exc

    expected_secret = os.getenv("WEBHOOK_SECRET", "")
    if not expected_secret or alert.secret != expected_secret:
        logger.warning("Tentativa de webhook com segredo inválido.")
        raise HTTPException(status_code=401, detail="Segredo inválido")

    verdict, reason = risk.check(alert.model_dump())
    if verdict == "BLOCK":
        logger.info("Sinal %s/%s bloqueado pelo filtro de risco: %s", alert.symbol, alert.event, reason)
        return {"status": "blocked", "reason": reason}

    message = format_message(alert)
    try:
        send_whatsapp_message(message)
    except WhatsAppError as exc:
        logger.error("Falha ao enviar WhatsApp: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    logger.info("Alerta %s/%s encaminhado para o WhatsApp.", alert.symbol, alert.event)
    return {"status": "sent"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)
