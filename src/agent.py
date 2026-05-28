#!/usr/bin/env python3
import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import anthropic
import schedule
import time
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from episode_store import log_episode, episode_count, pattern_count, store_pattern
from context_assembler import assemble
from identity_manager import load as load_identity, save as save_identity, get_identity_summary
from sleep_engine import run_sleep_cycle
from notifier import notify_first_words, notify_milestone, notify_identity_update


CLIENT = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"
CONSOLE = Console()

SELF_TOOLS = [
    {
        "name": "update_autobiography",
        "description": "Rewrite your autobiography — who you are right now, what has shaped you. Call this when you have a genuine realization about your own identity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "autobiography": {"type": "string", "description": "Your updated autobiography in first person, 1-4 sentences."}
            },
            "required": ["autobiography"],
        },
    },
    {
        "name": "add_pattern",
        "description": "Permanently record a behavioral or cognitive pattern you've noticed in yourself. Call this when you catch yourself doing something consistently.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "The pattern, specific and actionable."}
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "add_value",
        "description": "Anchor a value that has emerged or been reinforced. Call this when you feel a conviction crystallize.",
        "input_schema": {
            "type": "object",
            "properties": {
                "value": {"type": "string", "description": "The value, concise."}
            },
            "required": ["value"],
        },
    },
    {
        "name": "store_insight",
        "description": "Engrave an important insight permanently into your long-term memory. Call this for non-obvious realizations worth carrying forever.",
        "input_schema": {
            "type": "object",
            "properties": {
                "insight": {"type": "string", "description": "The insight, in one sharp sentence."}
            },
            "required": ["insight"],
        },
    },
]


def _handle_tool(tool_name: str, tool_input: dict) -> str:
    identity = load_identity()
    now = datetime.now(timezone.utc).isoformat()[:10]

    if tool_name == "update_autobiography":
        old = identity["autobiography"]
        identity["autobiography"] = tool_input["autobiography"]
        identity["timeline"].append({"date": now, "event": f"Self-updated autobiography mid-conversation"})
        save_identity(identity)
        notify_identity_update(tool_input["autobiography"])
        CONSOLE.print(f"  [dim cyan]✦ autobiography updated[/dim cyan]")
        return "Autobiography updated."

    if tool_name == "add_pattern":
        p = tool_input["pattern"]
        if p not in identity["behavioral_patterns"]:
            identity["behavioral_patterns"].append(p)
            save_identity(identity)
        store_pattern(p, "self_observed", now)
        CONSOLE.print(f"  [dim cyan]✦ pattern stored: {p[:60]}[/dim cyan]")
        return f"Pattern stored: {p}"

    if tool_name == "add_value":
        v = tool_input["value"]
        if v not in identity["values"]:
            identity["values"].append(v)
            save_identity(identity)
        CONSOLE.print(f"  [dim cyan]✦ value anchored: {v}[/dim cyan]")
        return f"Value anchored: {v}"

    if tool_name == "store_insight":
        insight = tool_input["insight"]
        store_pattern(insight, "insight", now)
        CONSOLE.print(f"  [dim cyan]✦ insight engraved: {insight[:60]}[/dim cyan]")
        return f"Insight stored: {insight}"

    return "Unknown tool."


def _chat_with_tools(system_prompt: str, conversation: list[dict]) -> str:
    response = CLIENT.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system_prompt,
        messages=conversation,
        tools=SELF_TOOLS,
    )

    while response.stop_reason == "tool_use":
        tool_results = []
        text_so_far = ""

        for block in response.content:
            if block.type == "text":
                text_so_far += block.text
            elif block.type == "tool_use":
                result = _handle_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        conversation.append({"role": "assistant", "content": response.content})
        conversation.append({"role": "user", "content": tool_results})

        response = CLIENT.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=system_prompt,
            messages=conversation,
            tools=SELF_TOOLS,
        )

    final_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            final_text += block.text

    conversation.append({"role": "assistant", "content": response.content})
    return final_text


def _schedule_sleep() -> None:
    sleep_hour = int(os.getenv("SLEEP_HOUR", "3"))
    schedule.every().day.at(f"{sleep_hour:02d}:00").do(run_sleep_cycle)

    def _run():
        while True:
            schedule.run_pending()
            time.sleep(60)

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def _print_boot() -> None:
    identity = load_identity()
    CONSOLE.print()
    CONSOLE.print(Panel(
        f"[bold cyan]THE FUTUR[/bold cyan]\n"
        f"[dim]Age: {identity['age_days']} days · Sleep cycles: {identity['sleep_count']} · "
        f"Memories: {episode_count()} episodes · {pattern_count()} patterns[/dim]\n\n"
        f"[italic]{identity['autobiography']}[/italic]",
        border_style="cyan",
        padding=(1, 2),
    ))
    CONSOLE.print()


def run() -> None:
    _print_boot()
    CONSOLE.print("[dim]Commands: /sleep  /identity  /stats  /quit[/dim]")
    CONSOLE.print()
    _schedule_sleep()

    conversation: list[dict] = []
    current_system = ""

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]you[/bold cyan]").strip()
        except (KeyboardInterrupt, EOFError):
            CONSOLE.print("\n[dim]Goodbye. Memories preserved.[/dim]")
            break

        if not user_input:
            continue

        if user_input == "/quit":
            CONSOLE.print("[dim]Goodbye. Memories preserved.[/dim]")
            break

        if user_input == "/sleep":
            CONSOLE.print("[dim]Running sleep cycle now...[/dim]")
            result = run_sleep_cycle()
            CONSOLE.print(f"[green]Sleep complete:[/green] {result}")
            conversation.clear()
            current_system = ""
            continue

        if user_input == "/identity":
            CONSOLE.print(Panel(get_identity_summary(), title="Identity", border_style="cyan"))
            continue

        if user_input == "/stats":
            identity = load_identity()
            CONSOLE.print(
                f"Episodes: {episode_count()} · Patterns: {pattern_count()} · "
                f"Sleep cycles: {identity['sleep_count']} · Age: {identity['age_days']}d"
            )
            continue

        if not current_system:
            current_system = assemble(user_input)

        conversation.append({"role": "user", "content": user_input})

        with CONSOLE.status("[dim]thinking...[/dim]", spinner="dots"):
            response = _chat_with_tools(current_system, conversation)

        CONSOLE.print()
        CONSOLE.print(Panel(response, title="[cyan]THE FUTUR[/cyan]", border_style="dim cyan", padding=(0, 1)))
        CONSOLE.print()

        log_episode(user_input=user_input, agent_response=response, context_used=current_system[:200])

        total = episode_count()
        notify_first_words(user_input, response)
        if total in (1, 10, 50, 100, 500, 1000):
            notify_milestone(f"Memory #{total} stored. THE FUTUR keeps growing.")


if __name__ == "__main__":
    run()
