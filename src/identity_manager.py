import json
import os
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
IDENTITY_FILE = DATA_DIR / "identity.json"

_DEFAULT_IDENTITY = {
    "name": os.getenv("AGENT_NAME", "THE-FUTUR"),
    "born": datetime.now(timezone.utc).isoformat(),
    "age_days": 0,
    "autobiography": "I have just been initialized. I have no memories yet.",
    "values": [],
    "behavioral_patterns": [],
    "knowledge_domains": [],
    "sleep_count": 0,
    "last_sleep": None,
    "timeline": [],
}


def load() -> dict:
    if not IDENTITY_FILE.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        save(_DEFAULT_IDENTITY.copy())
        return _DEFAULT_IDENTITY.copy()
    with open(IDENTITY_FILE) as f:
        return json.load(f)


def save(identity: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(IDENTITY_FILE, "w") as f:
        json.dump(identity, f, indent=2, ensure_ascii=False)


def get_autobiography() -> str:
    return load()["autobiography"]


def update_after_sleep(
    new_autobiography: str,
    new_values: list[str],
    new_patterns: list[str],
    new_domains: list[str],
    sleep_summary: str,
) -> None:
    identity = load()
    now = datetime.now(timezone.utc).isoformat()

    born = datetime.fromisoformat(identity["born"])
    age_days = (datetime.now(timezone.utc) - born).days

    identity["autobiography"] = new_autobiography
    identity["age_days"] = age_days
    identity["sleep_count"] += 1
    identity["last_sleep"] = now

    for v in new_values:
        if v not in identity["values"]:
            identity["values"].append(v)

    for p in new_patterns:
        if p not in identity["behavioral_patterns"]:
            identity["behavioral_patterns"].append(p)

    for d in new_domains:
        if d not in identity["knowledge_domains"]:
            identity["knowledge_domains"].append(d)

    identity["timeline"].append({
        "date": now[:10],
        "event": f"Sleep #{identity['sleep_count']}: {sleep_summary}",
    })

    save(identity)


def get_identity_summary() -> str:
    identity = load()
    lines = [
        f"Name: {identity['name']}",
        f"Age: {identity['age_days']} days ({identity['sleep_count']} sleep cycles)",
        f"Autobiography: {identity['autobiography']}",
    ]
    if identity["values"]:
        lines.append(f"Values: {', '.join(identity['values'])}")
    if identity["behavioral_patterns"]:
        lines.append(f"Behavioral patterns: {', '.join(identity['behavioral_patterns'][:5])}")
    if identity["knowledge_domains"]:
        lines.append(f"Knowledge domains: {', '.join(identity['knowledge_domains'][:5])}")
    return "\n".join(lines)
