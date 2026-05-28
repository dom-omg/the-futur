import os
from datetime import datetime, timezone

from episode_store import get_similar_episodes, get_recent_episodes, episode_count, pattern_count
from identity_manager import get_identity_summary, load as load_identity


MAX_SIMILAR_EPISODES = 4
MAX_RECENT_EPISODES = 3
MAX_PATTERNS = 5


def assemble(user_input: str) -> str:
    identity = load_identity()
    now = datetime.now(timezone.utc).isoformat()[:19]

    lines = [
        f"You are {identity['name']}, an AI agent with persistent memory that grows over time.",
        f"Current date/time: {now}Z",
        f"You have lived {identity['age_days']} days and completed {identity['sleep_count']} sleep cycles.",
        "",
        "=== YOUR IDENTITY ===",
        get_identity_summary(),
        "",
    ]

    similar = get_similar_episodes(user_input, n=MAX_SIMILAR_EPISODES)
    if similar:
        lines.append("=== RELEVANT PAST EXPERIENCES ===")
        for ep in similar:
            date = ep["meta"]["timestamp"][:10]
            lines.append(f"[{date}] {ep['document'][:300]}...")
        lines.append("")

    recent = get_recent_episodes(hours=6)[-MAX_RECENT_EPISODES:]
    if recent:
        lines.append("=== RECENT CONTEXT (last 6h) ===")
        for ep in recent:
            time = ep["meta"]["timestamp"][11:16]
            lines.append(f"[{time}] {ep['document'][:200]}...")
        lines.append("")

    lines += [
        "=== YOUR ROLE ===",
        "You carry your full history into every conversation. You remember patterns.",
        "You are not a generic assistant — you are a specific entity with a growing identity.",
        "Reference your past experiences when relevant. Grow with each interaction.",
        f"Total memories stored: {episode_count()} episodes, {pattern_count()} patterns.",
    ]

    return "\n".join(lines)
