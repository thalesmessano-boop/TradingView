"""Testes do filtro de risco (PASS/BLOCK) aplicado aos sinais recebidos."""
import json

import pytest

import risk

BASE_ALERT = {
    "symbol": "XAUUSD",
    "side": "BUY",
    "event": "BOS",
    "timeframe": "15",
    "entry": 2415.30,
    "stop_loss": 2408.50,
    "take_profit": 2428.90,
    "rr": 2.0,
}


@pytest.fixture(autouse=True)
def trader_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADER_DATA_DIR", str(tmp_path))
    yield tmp_path


def test_pass_within_limits():
    verdict, reason = risk.check(dict(BASE_ALERT))
    assert verdict == "PASS"
    assert reason is None


def test_blocks_duplicate_within_cooldown():
    risk.check(dict(BASE_ALERT))
    verdict, reason = risk.check(dict(BASE_ALERT))
    assert verdict == "BLOCK"
    assert "duplicado" in reason


def test_allows_after_cooldown_with_different_timeframe():
    risk.check(dict(BASE_ALERT))
    verdict, _ = risk.check({**BASE_ALERT, "timeframe": "60"})
    assert verdict == "PASS"


def test_blocks_low_rr():
    verdict, reason = risk.check({**BASE_ALERT, "rr": 1.0})
    assert verdict == "BLOCK"
    assert "R:R" in reason


def test_blocks_stop_too_tight():
    verdict, reason = risk.check({**BASE_ALERT, "stop_loss": 2415.00})
    assert verdict == "BLOCK"
    assert "abaixo do mínimo" in reason


def test_blocks_stop_too_wide():
    verdict, reason = risk.check({**BASE_ALERT, "stop_loss": 2350.00})
    assert verdict == "BLOCK"
    assert "acima do máximo" in reason


def test_blocks_daily_cap(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"max_signals_per_day": 1, "cooldown_minutes": 0}))
    risk.check({**BASE_ALERT, "side": "BUY"})
    verdict, reason = risk.check({**BASE_ALERT, "side": "SELL"})
    assert verdict == "BLOCK"
    assert "limite diário" in reason


def test_logs_every_verdict(tmp_path):
    risk.check(dict(BASE_ALERT))
    risk.check({**BASE_ALERT, "rr": 1.0})
    log_lines = (tmp_path / "state" / "risk_log.jsonl").read_text().splitlines()
    assert len(log_lines) == 2
    verdicts = [json.loads(line)["verdict"] for line in log_lines]
    assert verdicts == ["PASS", "BLOCK"]
