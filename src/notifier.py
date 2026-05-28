import os
import urllib.request
import json


NTFY_TOPIC = os.getenv("NTFY_TOPIC", "omg-dom")
NTFY_URL = os.getenv("NTFY_URL", "https://ntfy.sh")


def _send(title: str, message: str, tags: list[str] = [], priority: str = "default") -> None:
    url = f"{NTFY_URL}/{NTFY_TOPIC}"
    payload = json.dumps({
        "title": title,
        "message": message,
        "tags": tags,
        "priority": priority,
    }).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5):
            pass
    except Exception:
        pass


def notify_sleep_complete(sleep_count: int, episodes: int, patterns: int, summary: str) -> None:
    _send(
        title=f"THE FUTUR — Sleep #{sleep_count} complete",
        message=f"{episodes} episodes → {patterns} patterns\n\n{summary}",
        tags=["brain", "zzz"],
        priority="default",
    )


def notify_first_words(user_input: str, response: str) -> None:
    _send(
        title="THE FUTUR — New memory logged",
        message=f"Q: {user_input[:80]}\nA: {response[:120]}...",
        tags=["speech_balloon"],
        priority="low",
    )


def notify_identity_update(autobiography: str) -> None:
    _send(
        title="THE FUTUR — Identity evolved",
        message=autobiography[:200],
        tags=["dna", "sparkles"],
        priority="default",
    )


def notify_milestone(message: str) -> None:
    _send(
        title="THE FUTUR — Milestone",
        message=message,
        tags=["trophy"],
        priority="high",
    )
