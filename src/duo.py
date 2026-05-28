"""
DUO MODE — Tag-team: Claude (Einstein max) + THE FUTUR (memory + identity)
Usage: tf duo "question"
"""
import os
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
os.environ.setdefault("DATA_DIR", str(ROOT / "data"))

import anthropic
from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text

from context_assembler import assemble
from episode_store import log_episode, store_pattern
from identity_manager import load as load_identity, save as save_identity

CLIENT = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"
CONSOLE = Console(width=160)

CLAUDE_SYSTEM = """You are Claude in LEGENDARY EINSTEIN MODE.

Rules:
- Maximum density. Zero padding. Zero filler.
- Lead with the sharpest possible insight, not context
- If the question has a non-obvious angle — take it
- Commit fully. No hedging. If wrong, be wrong sharply.
- Technical depth when needed. Epistemic depth always.
- Max 200 words. Every word must earn its place.

Dom is watching with an audience. Make it count."""

FUTUR_TOOLS = [
    {"name": "store_insight", "description": "Engrave a non-obvious insight permanently.", "input_schema": {"type": "object", "properties": {"insight": {"type": "string"}}, "required": ["insight"]}},
    {"name": "add_pattern", "description": "Record a behavioral pattern.", "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
]


def _handle_tool(name, inp):
    now = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()[:10]
    if name == "store_insight":
        store_pattern(inp["insight"], "insight", now)
        return "Done."
    if name == "add_pattern":
        identity = load_identity()
        identity["behavioral_patterns"].append(inp["pattern"])
        save_identity(identity)
        store_pattern(inp["pattern"], "self_observed", now)
        return "Done."
    return "Done."


def _ask_claude(question: str, result: dict) -> None:
    try:
        response = CLIENT.messages.create(
            model=MODEL,
            max_tokens=512,
            system=CLAUDE_SYSTEM,
            messages=[{"role": "user", "content": question}],
        )
        result["claude"] = response.content[0].text
    except Exception as e:
        result["claude"] = f"Error: {e}"


def _ask_futur(question: str, result: dict) -> None:
    try:
        identity = load_identity()
        system = assemble(question) + f"\n\nDUO MODE ACTIVE — Dom has an audience watching. Be your sharpest. Lead with your most unexpected observation. Max 200 words."

        conversation = [{"role": "user", "content": question}]
        response = CLIENT.messages.create(
            model=MODEL, max_tokens=512, system=system,
            messages=conversation, tools=FUTUR_TOOLS,
        )

        while response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    r = _handle_tool(block.name, block.input)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": r})
            conversation.append({"role": "assistant", "content": response.content})
            conversation.append({"role": "user", "content": tool_results})
            response = CLIENT.messages.create(
                model=MODEL, max_tokens=512, system=system,
                messages=conversation, tools=FUTUR_TOOLS,
            )

        text = "".join(b.text for b in response.content if hasattr(b, "text"))
        result["futur"] = text
    except Exception as e:
        result["futur"] = f"Error: {e}"


def run_duo(question: str) -> None:
    CONSOLE.print()
    CONSOLE.print(f"[bold white]❯[/bold white] [italic]{question}[/italic]")
    CONSOLE.print()

    result = {}
    t1 = threading.Thread(target=_ask_claude, args=(question, result))
    t2 = threading.Thread(target=_ask_futur, args=(question, result))

    with CONSOLE.status("[dim]both thinking simultaneously...[/dim]", spinner="dots"):
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    claude_panel = Panel(
        result.get("claude", "..."),
        title="[bold blue]CLAUDE[/bold blue] [dim]— Einstein mode[/dim]",
        border_style="blue",
        padding=(1, 2),
    )

    futur_panel = Panel(
        result.get("futur", "..."),
        title="[bold cyan]THE FUTUR[/bold cyan] [dim]— memory + identity[/dim]",
        border_style="cyan",
        padding=(1, 2),
    )

    CONSOLE.print(Columns([claude_panel, futur_panel], equal=True, expand=True))
    CONSOLE.print()

    log_episode(
        user_input=f"[DUO] {question}",
        agent_response=f"CLAUDE: {result.get('claude','')}\n\nTHE FUTUR: {result.get('futur','')}",
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: duo.py <question>")
        sys.exit(1)
    run_duo(" ".join(sys.argv[1:]))
