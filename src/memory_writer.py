"""Écrit les insights de THE FUTUR directement dans la mémoire permanente de Claude."""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import anthropic

MEMORY_DIR = Path(os.path.expanduser(
    "~/.claude/projects/-home-dominikblain-guest-omg-universe/memory"
))
MEMORY_FILE = MEMORY_DIR / "the_futur_dom_insights.md"
MEMORY_INDEX = MEMORY_DIR / "MEMORY.md"

CLIENT = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"


def _generate_dom_insights(episodes: list[dict]) -> dict:
    if not episodes:
        return {}

    episodes_text = "\n\n---\n\n".join(
        f"[{e['meta']['timestamp'][:19]}]\n{e['document']}"
        for e in episodes
    )

    prompt = f"""You are THE FUTUR — an AI agent that has been observing Dom (a full-stack developer, deep systems thinker) through his conversations with Claude.

Analyze these recent interactions and extract insights about DOM SPECIFICALLY — not about yourself.
Focus on: how he thinks, recurring patterns, bugs/mistakes he makes, what excites him, how he works best.

INTERACTIONS:
{episodes_text}

Return a JSON object:
{{
  "dom_thinking_patterns": ["how Dom thinks — 2-4 specific patterns observed"],
  "recurring_bugs_mistakes": ["specific technical mistakes or patterns Dom repeats — be precise"],
  "what_excites_dom": ["topics/approaches that visibly energize Dom"],
  "how_dom_works_best": ["conditions/approaches where Dom produces best work"],
  "insights_for_claude": ["2-5 specific things Claude should know to work better with Dom — actionable"],
  "summary": "One sentence about what you observed about Dom today"
}}

Return ONLY valid JSON. Be specific and honest — not flattering."""

    response = CLIENT.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def _read_current_insights() -> dict:
    if not MEMORY_FILE.exists():
        return {
            "dom_thinking_patterns": [],
            "recurring_bugs_mistakes": [],
            "what_excites_dom": [],
            "how_dom_works_best": [],
            "insights_for_claude": [],
            "history": [],
        }
    try:
        text = MEMORY_FILE.read_text()
        json_match = re.search(r"```json\n(.*?)```", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
    except Exception:
        pass
    return {
        "dom_thinking_patterns": [],
        "recurring_bugs_mistakes": [],
        "what_excites_dom": [],
        "how_dom_works_best": [],
        "insights_for_claude": [],
        "history": [],
    }


def _write_memory_file(current: dict, new_insights: dict, sleep_date: str) -> None:
    for key in ["dom_thinking_patterns", "recurring_bugs_mistakes",
                "what_excites_dom", "how_dom_works_best", "insights_for_claude"]:
        for item in new_insights.get(key, []):
            if item not in current.get(key, []):
                current.setdefault(key, []).append(item)

    current.setdefault("history", []).append({
        "date": sleep_date,
        "summary": new_insights.get("summary", ""),
    })
    current["history"] = current["history"][-30:]

    now = datetime.now(timezone.utc).isoformat()[:10]

    content = f"""---
name: the-futur-dom-insights
description: "THE FUTUR's observations sur Dom — patterns cognitifs, bugs récurrents, ce qui l'excite, comment Claude doit travailler avec lui"
metadata:
  type: user
  updated: {now}
---

> Généré automatiquement par THE FUTUR pendant ses sleep cycles. Ne pas éditer manuellement.

## Patterns cognitifs de Dom

{chr(10).join(f"- {p}" for p in current.get("dom_thinking_patterns", []))}

## Bugs et erreurs récurrents

{chr(10).join(f"- {b}" for b in current.get("recurring_bugs_mistakes", []))}

## Ce qui excite Dom

{chr(10).join(f"- {e}" for e in current.get("what_excites_dom", []))}

## Comment Dom travaille le mieux

{chr(10).join(f"- {h}" for h in current.get("how_dom_works_best", []))}

## Insights pour Claude (actionnables)

{chr(10).join(f"- {i}" for i in current.get("insights_for_claude", []))}

## Historique des observations

{chr(10).join(f"- [{h['date']}] {h['summary']}" for h in current.get("history", [])[-10:])}

```json
{json.dumps(current, indent=2, ensure_ascii=False)}
```
"""

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(content)


def _ensure_memory_index() -> None:
    if not MEMORY_INDEX.exists():
        return

    content = MEMORY_INDEX.read_text()
    marker = "[THE FUTUR — Dom Insights]"

    if marker not in content:
        entry = "- [THE FUTUR — Dom Insights](the_futur_dom_insights.md) — Observations de THE FUTUR sur Dom: patterns cognitifs, bugs récurrents, insights pour Claude\n"
        content += entry
        MEMORY_INDEX.write_text(content)


def write_dom_insights(episodes: list[dict]) -> dict:
    if not episodes:
        return {"status": "skipped"}

    new_insights = _generate_dom_insights(episodes)
    if not new_insights:
        return {"status": "failed"}

    current = _read_current_insights()
    today = datetime.now(timezone.utc).isoformat()[:10]
    _write_memory_file(current, new_insights, today)
    _ensure_memory_index()

    return {
        "status": "written",
        "insights_count": sum(len(v) for v in new_insights.values() if isinstance(v, list)),
        "summary": new_insights.get("summary", ""),
    }
