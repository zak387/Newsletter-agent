#!/usr/bin/env python3
"""Strategy Agent — runs once per creator, produces a positioning brief."""

import argparse
import json
import sys
from pathlib import Path

# Ensure the project root is on sys.path when running this file directly.
_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from agents.strategy.session import Session
from agents.strategy.skills.public_research import run_public_research
from agents.strategy.skills.newsletter_research import run_newsletter_research
from agents.strategy.skills.trend_research import run_trend_research
from agents.strategy.renderer import render_brief

console = Console()

CATEGORIES = ["Jobs", "Hobbies", "Investments", "Personal transformation"]


def ask(prompt: str) -> str:
    """Pause and collect operator input."""
    return Prompt.ask(f"\n[bold cyan]{prompt}[/bold cyan]")


def step0_ingest(session: Session) -> dict:
    console.print(Panel("[bold]Step 0 — Data Ingestion[/bold]", style="blue"))

    if session.get("step0_done"):
        console.print("[dim]Step 0 already complete — loading from session.[/dim]")
        return session.get("step0_result")

    console.print("Enter the creator's public content URLs (one per line). Empty line to finish:")
    urls = []
    while True:
        url = input("> ").strip()
        if not url:
            break
        urls.append(url)

    human_context = ask("Any additional context? (engagement rate, products sold, audience signals — or press Enter to skip)")

    console.print("\n[dim]Running public research subagent...[/dim]")
    result = run_public_research(urls=urls, human_context=human_context)

    if result.get("gaps_flagged"):
        console.print("\n[yellow]Gaps flagged (research could not confirm these):[/yellow]")
        for gap in result["gaps_flagged"]:
            console.print(f"  • {gap}")

    session.set("step0_result", result)
    session.set("step0_done", True)
    session.save()
    return result


def step1_niche(session: Session, ingest_result: dict) -> str:
    console.print(Panel("[bold]Step 1 — Niche Classification[/bold]", style="blue"))

    if session.get("step1_done"):
        console.print("[dim]Step 1 already complete — loading from session.[/dim]")
        return session.get("niche_candidate")

    # Stage 1a — Category
    suggested_category = ingest_result.get("category_suggestion", "")
    console.print(f"\nSuggested primary category: [bold]{suggested_category}[/bold]")
    console.print(f"Available categories: {', '.join(CATEGORIES)}")
    category = ask("Confirm category or type a different one")

    # Stage 1b — Sub-niches
    sub_niches = ingest_result.get("sub_niches", [])
    console.print(f"\nSub-niches found in creator content:")
    for i, s in enumerate(sub_niches, 1):
        console.print(f"  {i}. {s}")

    selected = ask("Which sub-niches should we combine or prioritise? (type them, comma-separated)")

    # Stage 1c — Niche candidate
    niche_candidate = f"{category} > {selected}"
    console.print(f"\nNiche candidate: [bold]{niche_candidate}[/bold]")
    confirm = ask("Confirm this niche candidate? (yes / edit)")

    if confirm.lower() not in ("yes", "y"):
        niche_candidate = ask("Enter your preferred niche candidate")

    session.set("niche_candidate", niche_candidate)
    session.set("step1_done", True)
    session.save()
    return niche_candidate


def main():
    parser = argparse.ArgumentParser(description="Strategy Agent")
    parser.add_argument("--creator", required=True, help="Creator slug (e.g. jane-doe)")
    args = parser.parse_args()

    creator_slug = args.creator
    session = Session(creator_slug=creator_slug)

    console.print(Panel(f"[bold green]Strategy Agent[/bold green]\nCreator: {creator_slug}", style="green"))

    # Steps 0 and 1
    ingest_result = step0_ingest(session)
    niche_candidate = step1_niche(session, ingest_result)

    console.print(f"\n[green]Steps 0–1 complete. Niche candidate: {niche_candidate}[/green]")


if __name__ == "__main__":
    main()
