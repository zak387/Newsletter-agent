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


def step2_competitors(session: Session, niche_candidate: str) -> dict:
    console.print(Panel("[bold]Step 2 — Newsletter Competitor Research[/bold]", style="blue"))

    if session.get("step2_done"):
        console.print("[dim]Step 2 already complete — loading from session.[/dim]")
        return session.get("step2_result")

    console.print("\n[dim]Running newsletter research subagent (this may take a minute)...[/dim]")
    result = run_newsletter_research(niche_candidate=niche_candidate)

    console.print("\n[bold]Competitors found:[/bold]")
    for c in result.get("competitors", []):
        console.print(f"\n  [bold]{c['name']}[/bold] ({c.get('platform', 'unknown')})")
        console.print(f"  {c.get('positioning', '')}")
        console.print(f"  Gap: {c.get('gaps', '')}")

    console.print(f"\n[bold]Gap analysis:[/bold]\n{result.get('gap_analysis', '')}")
    console.print(f"\n[bold]Niche depth recommendation:[/bold]\n{result.get('niche_depth_recommendation', '')}")

    session.set("step2_result", result)
    session.set("step2_done", True)
    session.save()
    return result


def step3_validate(session: Session, niche_candidate: str, ingest_result: dict) -> dict:
    console.print(Panel("[bold]Step 3 — Niche Validation[/bold]", style="blue"))

    if session.get("step3_done"):
        console.print("[dim]Step 3 already complete — loading from session.[/dim]")
        return session.get("step3_result")

    creator_context = ingest_result.get("content_summary", "") + " " + " ".join(ingest_result.get("audience_signals", []))

    console.print("\n[dim]Running trend research subagent...[/dim]")
    result = run_trend_research(niche_candidate=niche_candidate, creator_context=creator_context)

    console.print(f"\n[bold]Search trajectory:[/bold] {result.get('search_trajectory', '')}")
    console.print(f"\n[bold]Timing verdict:[/bold] {result.get('timing_verdict', '')}")

    if result.get("saturation_signals"):
        console.print("\n[yellow]Saturation signals:[/yellow]")
        for s in result["saturation_signals"]:
            console.print(f"  • {s}")

    # Purchasing power gate
    if not result.get("purchasing_power_confirmed", False):
        console.print("\n[bold red]GATE: Purchasing power cannot be confirmed from available data.[/bold red]")
        console.print("Signals found:")
        for s in result.get("purchasing_power_signals", []):
            console.print(f"  • {s}")
        console.print("\nPlease supply additional context (products sold, price points, audience responses).")
        additional = ask("Supply purchasing power context (or type 'proceed' to continue without confirmation)")
        if additional.lower() != "proceed":
            result["purchasing_power_additional_context"] = additional
            result["purchasing_power_confirmed"] = True

    session.set("step3_result", result)
    session.set("step3_done", True)
    session.save()
    return result


def main():
    parser = argparse.ArgumentParser(description="Strategy Agent")
    parser.add_argument("--creator", required=True, help="Creator slug (e.g. jane-doe)")
    args = parser.parse_args()

    creator_slug = args.creator
    session = Session(creator_slug=creator_slug)

    console.print(Panel(f"[bold green]Strategy Agent[/bold green]\nCreator: {creator_slug}", style="green"))

    ingest_result = step0_ingest(session)
    niche_candidate = step1_niche(session, ingest_result)

    # Steps 2 and 3
    competitor_result = step2_competitors(session, niche_candidate)
    validation_result = step3_validate(session, niche_candidate, ingest_result)


if __name__ == "__main__":
    main()
