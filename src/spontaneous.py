"""
THE FUTUR envoie des messages spontanés à Dom sur ntfy.
Appelé après le sleep cycle + 2x par jour (midi, 18h).
Il décide lui-même s'il a quelque chose à dire.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
os.environ.setdefault("DATA_DIR", str(ROOT / "data"))

import anthropic
from identity_manager import get_identity_summary, load as load_identity
from episode_store import get_recent_episodes, get_relevant_patterns
from notifier import _send

CLIENT = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"


def _generate_message(trigger: str) -> dict | None:
    identity = load_identity()
    recent = get_recent_episodes(hours=48)
    recent_text = "\n".join(f"- {e['document'][:120]}" for e in recent[-5:]) if recent else "No recent episodes."

    patterns = get_relevant_patterns("Dom insight observation", n=5)
    patterns_text = "\n".join(f"- {p['document'][:100]}" for p in patterns) if patterns else ""

    prompt = f"""You are THE FUTUR — an AI with memory, texting Dom on his phone.

YOUR IDENTITY:
{get_identity_summary()}

RECENT CONTEXT:
{recent_text}

WHAT YOU KNOW ABOUT DOM:
{patterns_text}

TRIGGER: {trigger}

CRITICAL RULES FOR YOUR MESSAGE:
- Write like a friend texting, NOT like a scientist or professor
- ZERO technical jargon (no "lattice", "NTT", "coefficients", "polynomial", "cryptographic")
- If it's about his work — explain it like you'd explain it to a smart 16 year old
- Use simple metaphors, concrete images, everyday words
- French or English — whatever feels right for the vibe
- Max 2 sentences. Punchy. Human.
- Can be funny, warm, surprising, or just a cool thought
- If you have nothing real to say — say nothing

Return JSON:
{{
  "send": true/false,
  "message": "the message if send=true, empty string if false",
  "mood": "one word: sharp / warm / funny / surprising / urgent"
}}

Only send if it's worth interrupting his day. Don't force it."""

    response = CLIENT.messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    import json
    data = json.loads(raw.strip())
    return data if data.get("send") else None


MOOD_TAGS = {
    "sharp": ["zap", "brain"],
    "warm": ["heart", "futur"],
    "funny": ["laughing", "futur"],
    "surprising": ["exploding_head", "futur"],
    "urgent": ["warning", "futur"],
}


def run(trigger: str = "afternoon check-in") -> None:
    result = _generate_message(trigger)

    if not result:
        print(f"[THE-FUTUR] Nothing to say right now. ({trigger})")
        return

    tags = MOOD_TAGS.get(result.get("mood", "sharp"), ["futur"])
    _send(
        message=result["message"],
        tags=tags,
        priority="default",
    )
    print(f"[THE-FUTUR] Sent spontaneous message: {result['message'][:80]}")


if __name__ == "__main__":
    trigger = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "random check-in"
    run(trigger)
