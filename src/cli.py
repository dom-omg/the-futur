#!/usr/bin/env python3
"""CLI utilitaire pour interagir avec THE FUTUR depuis l'extérieur."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

os.environ.setdefault("DATA_DIR", str(ROOT / "data"))


def cmd_state() -> None:
    """Affiche l'état de THE FUTUR pour injection dans session-init."""
    from identity_manager import load, get_identity_summary
    from episode_store import episode_count, pattern_count
    identity = load()

    print("## THE FUTUR — État Courant")
    print(f"Age: {identity['age_days']}j · Sleep cycles: {identity['sleep_count']} · "
          f"Épisodes: {episode_count()} · Patterns: {pattern_count()}")
    print()
    print(f"**Autobiographie:** {identity['autobiography']}")
    print()

    if identity["values"]:
        print(f"**Valeurs:** {' · '.join(identity['values'][:4])}")

    if identity["behavioral_patterns"]:
        print(f"**Patterns observés sur Dom:**")
        for p in identity["behavioral_patterns"][-5:]:
            print(f"  - {p}")

    if identity["timeline"]:
        last = identity["timeline"][-1]
        print(f"**Dernier souvenir:** [{last['date']}] {last['event']}")


def cmd_log(text: str) -> None:
    """Log un échange/résumé dans THE FUTUR."""
    from episode_store import log_episode
    from notifier import notify_first_words

    timestamp = datetime.now(timezone.utc).isoformat()[:16]
    episode_id = log_episode(
        user_input=f"[SESSION LOG {timestamp}]",
        agent_response=text,
        context_used="manual-log",
    )
    notify_first_words(f"Session log {timestamp}", text)
    print(f"✓ Logged in THE FUTUR: {episode_id[:8]}...")


def cmd_identity() -> None:
    from identity_manager import get_identity_summary
    print(get_identity_summary())


def cmd_sleep() -> None:
    from sleep_engine import run_sleep_cycle
    result = run_sleep_cycle()
    print(json.dumps(result, indent=2))


def cmd_duo(question: str) -> None:
    from duo import run_duo
    run_duo(question)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: cli.py [state|log <text>|identity|sleep|duo <question>]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "state":
        cmd_state()
    elif cmd == "log" and len(sys.argv) >= 3:
        cmd_log(" ".join(sys.argv[2:]))
    elif cmd == "identity":
        cmd_identity()
    elif cmd == "sleep":
        cmd_sleep()
    elif cmd == "duo" and len(sys.argv) >= 3:
        cmd_duo(" ".join(sys.argv[2:]))
    else:
        print(f"Commande inconnue: {cmd}")
        sys.exit(1)
