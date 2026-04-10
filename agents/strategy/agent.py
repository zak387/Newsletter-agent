#!/usr/bin/env python3
"""Strategy Agent — runs once per creator, produces a strategy brief."""

import argparse
import json
import re
import sys
from pathlib import Path

import anthropic as _anthropic

# Ensure the project root is on sys.path when running this file directly.
_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from dotenv import load_dotenv
load_dotenv(_project_root / ".env")

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
        result = session.get("step0_result")
        if result is None:
            raise RuntimeError("Session claims step0 is done but step0_result is missing. Delete the session file and re-run.")
        return result

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
        niche = session.get("niche_candidate")
        if niche is None:
            raise RuntimeError("Session claims step1 is done but niche_candidate is missing. Delete the session file and re-run.")
        return niche

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
        result = session.get("step2_result")
        if result is None:
            raise RuntimeError("Session claims step2 is done but step2_result is missing. Delete the session file and re-run.")
        return result

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
        result = session.get("step3_result")
        if result is None:
            raise RuntimeError("Session claims step3 is done but step3_result is missing. Delete the session file and re-run.")
        return result

    creator_context = (ingest_result.get("content_summary") or "") + " " + " ".join(ingest_result.get("audience_signals") or [])

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
        if additional.lower() == "proceed":
            # Operator explicitly chose to proceed without confirmation
            result["purchasing_power_confirmed"] = False
        else:
            result["purchasing_power_additional_context"] = additional
            result["purchasing_power_confirmed"] = True

    session.set("step3_result", result)
    session.set("step3_done", True)
    session.save()
    return result


def step4_intake(session: Session, validation_result: dict, ingest_result: dict) -> dict:
    console.print(Panel("[bold]Step 4 — Creator Intake Questions[/bold]", style="blue"))

    if session.get("step4_done"):
        console.print("[dim]Step 4 already complete — loading from session.[/dim]")
        result = session.get("step4_result")
        if result is None:
            raise RuntimeError("Session claims step4 is done but step4_result is missing. Delete the session file and re-run.")
        return result

    console.print("\nThese questions must be answered before synthesis. Answer on behalf of the creator or pass them along.\n")

    answers = {}

    answers["origin_story"] = ask(
        "1. What is the specific moment or experience that led this creator to this topic? (Not the polished version — the real one)"
    )
    answers["contrarian_belief"] = ask(
        "2. What does this creator believe that most people in this space get wrong?"
    )
    answers["hidden_credibility"] = ask(
        "3. What has this creator done, experienced, or built that gives them credibility here that is NOT obvious from their public content?"
    )
    answers["ideal_reader"] = ask(
        "4. Who is the single most specific reader this newsletter is for? Picture one person — who are they and what are they struggling with right now?"
    )

    # Gap-specific questions
    if not validation_result.get("purchasing_power_confirmed") and not validation_result.get("purchasing_power_additional_context"):
        answers["purchasing_power_detail"] = ask(
            "What products has this creator's audience bought, at what price point, and how did they respond? (or press Enter to skip)"
        )

    archetype_ambiguous = not ingest_result.get("category_suggestion")
    if archetype_ambiguous:
        answers["self_archetype"] = ask(
            "How does this creator think of themselves: practitioner, learner, experimenter, or curator? (or press Enter to skip)"
        )

    session.set("step4_result", answers)
    session.set("step4_done", True)
    session.save()
    return answers


def step5_synthesise(
    session: Session,
    niche_candidate: str,
    ingest_result: dict,
    competitor_result: dict,
    validation_result: dict,
    intake_answers: dict,
    learnings: list,
) -> dict:
    console.print(Panel("[bold]Step 5 — Synthesis Pass[/bold]", style="blue"))

    client = _anthropic.Anthropic()

    learnings_block = ""
    if learnings:
        learnings_block = "\n\nPrevious revision learnings to apply:\n" + json.dumps(learnings, indent=2)

    prompt = f"""You are synthesising a strategy brief for a newsletter creator. Use ALL of the research and intake data below to fill every field. Where you cannot confirm a field from the data, leave the value as null.

Niche candidate: {niche_candidate}

Public research findings:
{json.dumps(ingest_result, indent=2)}

Competitor research:
{json.dumps(competitor_result, indent=2)}

Trend and validation data:
{json.dumps(validation_result, indent=2)}

Creator intake answers:
{json.dumps(intake_answers, indent=2)}
{learnings_block}

Return ONLY a JSON object with these exact keys:
{{
  "newsletter_name": ["name1", "name2", "name3"],
  "newsletter_name_rationale": ["rationale1", "rationale2", "rationale3"],
  "niche_umbrella": "string or null",
  "niche_rationale": "string or null",
  "target_reader": "string or null",
  "newsletter_statement": "string or null",
  "why_exist": "string or null",
  "why_creator": "string or null",
  "content_pillars": [
    {{"name": "string", "description": "string"}},
    {{"name": "string", "description": "string"}},
    {{"name": "string", "description": "string"}}
  ],
  "creator_archetype": {{
    "primary": "Expert | Student | Experimenter | Tastemaker",
    "secondary": "string or null",
    "evidence": "string"
  }},
  "business_model": "string",
  "competitor_insight": "string or null",
  "comparable_newsletter": "string or null"
}}"""

    console.print("\n[dim]Running synthesis subagent...[/dim]")
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    try:
        brief = json.loads(raw.strip())
    except json.JSONDecodeError as e:
        console.print(f"\n[bold red]Synthesis failed — model returned malformed JSON.[/bold red]")
        console.print(f"Raw output:\n{raw[:500]}")
        raise RuntimeError(f"Synthesis JSON parse error: {e}") from e

    session.set("brief", brief)
    session.set("step5_done", True)
    session.save()
    return brief


def step6_review(
    session: Session,
    brief: dict,
    niche_candidate: str,
    ingest_result: dict,
    competitor_result: dict,
    validation_result: dict,
    intake_answers: dict,
    creator_slug: str,
) -> dict:
    console.print(Panel("[bold]Step 6 — Human Review[/bold]", style="blue"))

    if session.get("locked"):
        console.print("[dim]Brief already locked — loading from session.[/dim]")
        brief = session.get("brief")
        if brief is None:
            raise RuntimeError("Session claims brief is locked but brief data is missing. Delete the session file and re-run.")
        return brief

    round_number = 0

    while True:
        round_number += 1
        md = render_brief(brief)
        console.print(Panel(md, title=f"Strategy Brief (Round {round_number})", style="white"))

        feedback = ask('Review the brief above. Type feedback to revise, or "lock it" to finalise')

        if feedback.strip().lower() in ("lock it", "lock", "done", "approve", "confirmed"):
            break

        # Store learning
        session.append_learning({"round": round_number, "feedback": feedback})
        session.save()

        console.print("\n[dim]Applying feedback and regenerating brief...[/dim]")
        brief = step5_synthesise(
            session=session,
            niche_candidate=niche_candidate,
            ingest_result=ingest_result,
            competitor_result=competitor_result,
            validation_result=validation_result,
            intake_answers=intake_answers,
            learnings=session.learnings,
        )

    # Write outputs
    briefs_dir = _project_root / "briefs" / creator_slug
    briefs_dir.mkdir(parents=True, exist_ok=True)
    md_path = briefs_dir / "strategy-brief.md"
    md_path.write_text(render_brief(brief), encoding="utf-8")

    session.save_brief_json(brief)
    session.set("locked", True)
    session.save()

    console.print(f"\n[bold green]Brief locked.[/bold green]")
    console.print(f"Markdown: {md_path}")
    return brief


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

    # Step 4
    intake_answers = step4_intake(session, validation_result, ingest_result)

    # Step 5
    brief = step5_synthesise(
        session=session,
        niche_candidate=niche_candidate,
        ingest_result=ingest_result,
        competitor_result=competitor_result,
        validation_result=validation_result,
        intake_answers=intake_answers,
        learnings=session.learnings,
    )

    # Step 6
    step6_review(
        session=session,
        brief=brief,
        niche_candidate=niche_candidate,
        ingest_result=ingest_result,
        competitor_result=competitor_result,
        validation_result=validation_result,
        intake_answers=intake_answers,
        creator_slug=creator_slug,
    )


if __name__ == "__main__":
    main()
