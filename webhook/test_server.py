"""Testes automatizados do servidor de webhook (sem enviar WhatsApp real)."""
import pytest
from fastapi.testclient import TestClient

import server
import whatsapp

client = TestClient(server.app)

PAYLOAD = {
    "secret": "test-secret",
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


@pytest.fixture(autouse=True)
def webhook_secret(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "test-secret")


@pytest.fixture(autouse=True)
def trader_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADER_DATA_DIR", str(tmp_path))


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_webhook_rejects_wrong_secret():
    resp = client.post("/webhook/tradingview", json={**PAYLOAD, "secret": "wrong"})
    assert resp.status_code == 401


def test_webhook_rejects_invalid_payload():
    resp = client.post("/webhook/tradingview", json={"secret": "test-secret"})
    assert resp.status_code == 422


def test_webhook_sends_formatted_message(monkeypatch):
    sent = {}

    def fake_send(text):
        sent["text"] = text

    monkeypatch.setattr(server, "send_whatsapp_message", fake_send)

    resp = client.post("/webhook/tradingview", json=PAYLOAD)

    assert resp.status_code == 200
    assert resp.json() == {"status": "sent"}
    assert "COMPRA" in sent["text"]
    assert "2415.30" in sent["text"]
    assert "2408.50" in sent["text"]
    assert "2428.90" in sent["text"]


def test_webhook_blocks_duplicate_signal(monkeypatch):
    sent = []
    monkeypatch.setattr(server, "send_whatsapp_message", sent.append)

    first = client.post("/webhook/tradingview", json=PAYLOAD)
    second = client.post("/webhook/tradingview", json=PAYLOAD)

    assert first.status_code == 200
    assert first.json() == {"status": "sent"}
    assert second.status_code == 200
    assert second.json()["status"] == "blocked"
    assert len(sent) == 1


def test_webhook_returns_502_on_whatsapp_failure(monkeypatch):
    def fake_send(text):
        raise whatsapp.WhatsAppError("falha simulada")

    monkeypatch.setattr(server, "send_whatsapp_message", fake_send)

    resp = client.post("/webhook/tradingview", json=PAYLOAD)
    assert resp.status_code == 502
