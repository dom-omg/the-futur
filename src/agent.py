#!/usr/bin/env python3
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
from rich.text import Text
from rich.rule import Rule

from episode_store import log_episode, episode_count, pattern_count
from context_assembler import assemble
from identity_manager import load as load_identity, get_identity_summary
from sleep_engine import run_sleep_cycle


CLIENT = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"
CONSOLE = Console()


def _chat(system_prompt: str, conversation: list[dict]) -> str:
    response = CLIENT.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system_prompt,
        messages=conversation,
    )
    return response.content[0].text


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


def _print_commands() -> None:
    CONSOLE.print("[dim]Commands: /sleep  /identity  /stats  /quit[/dim]")
    CONSOLE.print()


def run() -> None:
    _print_boot()
    _print_commands()
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
            response = _chat(current_system, conversation)

        conversation.append({"role": "assistant", "content": response})

        CONSOLE.print()
        CONSOLE.print(Panel(response, title="[cyan]THE FUTUR[/cyan]", border_style="dim cyan", padding=(0, 1)))
        CONSOLE.print()

        log_episode(
            user_input=user_input,
            agent_response=response,
            context_used=current_system[:200],
        )


if __name__ == "__main__":
    run()
