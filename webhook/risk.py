"""
Risk gate for incoming TradingView signals, in the same PASS/BLOCK spirit as
trader-skill's trader-risk: every signal is checked against configurable
limits before it reaches WhatsApp. A BLOCK is logged, never sent in full —
the pipeline stays fully automatic, so there is no "type yes" step here.
"""
import json
import os
import time
from pathlib import Path

DEFAULT_CONFIG = {
    "cooldown_minutes": 15,
    "max_signals_per_day": 6,
    "min_rr": 1.5,
    "min_stop_distance_usd": 1.0,
    "max_stop_distance_usd": 50.0,
}


def _trader_dir() -> Path:
    return Path(os.getenv("TRADER_DATA_DIR", Path(__file__).parent / "trader"))


def _config_path() -> Path:
    return _trader_dir() / "config.json"


def _state_path() -> Path:
    return _trader_dir() / "state" / "alerts_state.json"


def _log_path() -> Path:
    return _trader_dir() / "state" / "risk_log.jsonl"


def load_config() -> dict:
    config = dict(DEFAULT_CONFIG)
    path = _config_path()
    if path.exists():
        config.update(json.loads(path.read_text()))
    return config


def _load_state() -> dict:
    path = _state_path()
    if path.exists():
        return json.loads(path.read_text())
    return {"signals": []}


def _save_state(state: dict) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2))


def _log_verdict(alert: dict, verdict: str, reason: str | None) -> None:
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.time(),
        "verdict": verdict,
        "reason": reason,
        "symbol": alert.get("symbol"),
        "side": alert.get("side"),
        "event": alert.get("event"),
        "timeframe": alert.get("timeframe"),
        "entry": alert.get("entry"),
        "stop_loss": alert.get("stop_loss"),
        "take_profit": alert.get("take_profit"),
        "rr": alert.get("rr"),
    }
    with path.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")


def check(alert: dict) -> tuple[str, str | None]:
    """Checks one TradingView signal against the configured limits.

    Returns (verdict, reason): verdict is "PASS" or "BLOCK", reason is set
    only for a BLOCK. A PASS is recorded for the next call's cooldown/daily
    cap checks; every verdict (PASS or BLOCK) is appended to the risk log.
    """
    config = load_config()
    state = _load_state()
    now = time.time()
    signals = [s for s in state["signals"] if now - s["ts"] < 86400]

    def blocked(reason: str) -> tuple[str, str]:
        _log_verdict(alert, "BLOCK", reason)
        return "BLOCK", reason

    cooldown = config["cooldown_minutes"] * 60
    for s in reversed(signals):
        if s["side"] == alert["side"] and s["event"] == alert["event"] and s["timeframe"] == alert["timeframe"]:
            if now - s["ts"] < cooldown:
                return blocked(f"duplicado: mesmo lado/evento há menos de {config['cooldown_minutes']} min")
            break

    if len(signals) >= config["max_signals_per_day"]:
        return blocked(f"limite diário de {config['max_signals_per_day']} sinais atingido")

    if alert["rr"] < config["min_rr"]:
        return blocked(f"R:R {alert['rr']:.1f} abaixo do mínimo configurado ({config['min_rr']})")

    stop_distance = abs(alert["entry"] - alert["stop_loss"])
    if stop_distance < config["min_stop_distance_usd"]:
        return blocked(
            f"stop a {stop_distance:.2f} USD do preço, abaixo do mínimo ({config['min_stop_distance_usd']})"
        )
    if stop_distance > config["max_stop_distance_usd"]:
        return blocked(
            f"stop a {stop_distance:.2f} USD do preço, acima do máximo ({config['max_stop_distance_usd']})"
        )

    signals.append({"ts": now, "side": alert["side"], "event": alert["event"], "timeframe": alert["timeframe"]})
    state["signals"] = signals
    _save_state(state)
    _log_verdict(alert, "PASS", None)
    return "PASS", None
