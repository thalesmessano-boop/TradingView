#!/usr/bin/env python3
"""CLI para inspecionar e ajustar o filtro de risco do webhook XAU/USD."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_TRADER_DIR = Path("webhook/trader")


def _log_path(trader_dir: Path) -> Path:
    return trader_dir / "state" / "risk_log.jsonl"


def _config_path(trader_dir: Path) -> Path:
    return trader_dir / "config.json"


def cmd_log(args):
    path = _log_path(args.trader_dir)
    if not path.exists():
        print("Nenhum sinal registrado ainda.")
        return
    entries = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if args.only:
        entries = [e for e in entries if e["verdict"].lower() == args.only.lower()]
    for entry in entries[-args.limit :]:
        ts = datetime.fromtimestamp(entry["ts"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        line = (
            f"{ts}  {entry['verdict']:5s}  {entry.get('side', '?'):4s} {entry.get('event', '?'):5s}"
            f"  entry={entry.get('entry')}"
        )
        if entry["verdict"] == "BLOCK":
            line += f"  motivo: {entry['reason']}"
        print(line)


def cmd_show(args):
    path = _config_path(args.trader_dir)
    if path.exists():
        print(path.read_text())
        return
    example = path.parent / "config.example.json"
    print(f"{path} não existe ainda (usando os valores padrão do risk.py).")
    if example.exists():
        print(f"Exemplo em {example}:")
        print(example.read_text())


def cmd_set(args):
    path = _config_path(args.trader_dir)
    config = json.loads(path.read_text()) if path.exists() else {}
    try:
        value = json.loads(args.value)
    except json.JSONDecodeError:
        value = args.value
    config[args.key] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2))
    print(f"{args.key} = {value} (gravado em {path})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trader-dir", type=Path, default=DEFAULT_TRADER_DIR)
    sub = parser.add_subparsers(dest="command", required=True)

    p_log = sub.add_parser("log", help="mostra os últimos sinais recebidos (PASS/BLOCK)")
    p_log.add_argument("--limit", type=int, default=20)
    p_log.add_argument("--only", choices=["pass", "block"])
    p_log.set_defaults(func=cmd_log)

    p_show = sub.add_parser("show", help="mostra os limites de risco atuais")
    p_show.set_defaults(func=cmd_show)

    p_set = sub.add_parser("set", help="ajusta um limite, ex: set max_signals_per_day 10")
    p_set.add_argument("key")
    p_set.add_argument("value")
    p_set.set_defaults(func=cmd_set)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
