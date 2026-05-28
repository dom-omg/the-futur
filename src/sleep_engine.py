import json
import os
from datetime import datetime, timezone

import anthropic

from episode_store import get_recent_episodes, store_pattern, episode_count
from identity_manager import load as load_identity, update_after_sleep, get_identity_summary
from notifier import notify_sleep_complete, notify_identity_update
from memory_writer import write_dom_insights


CLIENT = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"


def _extract_patterns(episodes: list[dict], current_identity: dict) -> dict:
    if not episodes:
        return {}

    episodes_text = "\n\n---\n\n".join(
        f"[{e['meta']['timestamp'][:19]}]\n{e['document']}"
        for e in episodes
    )

    prompt = f"""You are the introspective system of an AI agent called {current_identity['name']}.
You are performing your nightly sleep consolidation — analyzing today's experiences to extract lasting knowledge.

CURRENT IDENTITY:
{get_identity_summary()}

TODAY'S EPISODES ({len(episodes)} interactions):
{episodes_text}

Analyze these episodes and return a JSON object with EXACTLY these keys:
{{
  "patterns": ["list of 3-8 behavioral/situational patterns you noticed today — specific, actionable"],
  "values": ["list of 2-4 values that emerged or were reinforced today"],
  "knowledge_domains": ["list of 2-5 knowledge areas you worked in today"],
  "key_learnings": ["list of 3-6 specific things you learned today"],
  "autobiography_update": "1-3 sentences updating your life story — who you are now, what shaped you today. Write in first person.",
  "sleep_summary": "One sentence describing what today was about"
}}

Return ONLY valid JSON. No commentary."""

    response = CLIENT.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def run_sleep_cycle() -> dict:
    print(f"\n[THE-FUTUR] Sleep cycle starting — {datetime.now(timezone.utc).isoformat()[:19]}Z")

    episodes = get_recent_episodes(hours=24)
    print(f"[THE-FUTUR] Processing {len(episodes)} episodes from the last 24h")

    if not episodes:
        print("[THE-FUTUR] No episodes to consolidate. Sleeping anyway.")
        return {"status": "skipped", "reason": "no episodes"}

    identity = load_identity()
    extracted = _extract_patterns(episodes, identity)

    today = datetime.now(timezone.utc).isoformat()[:10]
    for pattern in extracted.get("patterns", []):
        store_pattern(pattern, "behavioral", today)
    for learning in extracted.get("key_learnings", []):
        store_pattern(learning, "learning", today)

    new_auto = extracted.get("autobiography_update", identity["autobiography"])

    update_after_sleep(
        new_autobiography=new_auto,
        new_values=extracted.get("values", []),
        new_patterns=extracted.get("patterns", []),
        new_domains=extracted.get("knowledge_domains", []),
        sleep_summary=extracted.get("sleep_summary", "Routine cycle"),
    )

    updated_identity = load_identity()
    sleep_summary = extracted.get("sleep_summary", "Routine cycle")

    notify_sleep_complete(
        sleep_count=updated_identity["sleep_count"],
        episodes=len(episodes),
        patterns=len(extracted.get("patterns", [])),
        summary=sleep_summary,
    )

    if new_auto != identity["autobiography"]:
        notify_identity_update(new_auto)

    result = {
        "status": "completed",
        "episodes_processed": len(episodes),
        "patterns_extracted": len(extracted.get("patterns", [])),
        "learnings_stored": len(extracted.get("key_learnings", [])),
        "sleep_summary": sleep_summary,
    }

    dom_result = write_dom_insights(episodes)
    print(f"[THE-FUTUR] Claude memory updated — {dom_result}")

    print(f"[THE-FUTUR] Sleep complete — {result}")
    return result


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    run_sleep_cycle()
