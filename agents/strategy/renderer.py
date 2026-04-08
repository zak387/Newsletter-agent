def _field(value: str | None) -> str:
    return value if value else "_Not yet completed_"


def render_brief(brief: dict) -> str:
    lines = ["# Strategy Brief", ""]

    # Newsletter name
    lines += ["## Newsletter Name", ""]
    names = brief.get("newsletter_name") or []
    rationales = brief.get("newsletter_name_rationale") or []
    if names:
        for name, rationale in zip(names, rationales):
            lines.append(f"**{name}** — {rationale}")
    else:
        lines.append("_Not yet completed_")
    lines.append("")

    # Niche umbrella
    lines += ["## Niche Umbrella", ""]
    lines.append(_field(brief.get("niche_umbrella")))
    if brief.get("niche_rationale"):
        lines += ["", f"_{brief['niche_rationale']}_"]
    lines.append("")

    # Target reader
    lines += ["## Target Reader", ""]
    lines.append(_field(brief.get("target_reader")))
    lines.append("")

    # Newsletter statement
    lines += ["## Newsletter Statement", ""]
    lines.append(_field(brief.get("newsletter_statement")))
    lines.append("")

    # Why exist
    lines += ["## Why Does This Content Need to Exist?", ""]
    lines.append(_field(brief.get("why_exist")))
    lines.append("")

    # Why creator
    lines += ["## Why This Creator Specifically?", ""]
    lines.append(_field(brief.get("why_creator")))
    lines.append("")

    # Content pillars
    lines += ["## Content Pillars", ""]
    pillars = brief.get("content_pillars") or []
    if pillars:
        for i, pillar in enumerate(pillars, 1):
            name = pillar.get("name", "_Not yet completed_")
            description = pillar.get("description", "_Not yet completed_")
            lines.append(f"**{i}. {name}** — {description}")
    else:
        lines.append("_Not yet completed_")
    lines.append("")

    # Creator archetype
    lines += ["## Creator Archetype", ""]
    archetype = brief.get("creator_archetype")
    if archetype:
        label = archetype.get("primary", "_Not yet completed_")
        if archetype.get("secondary"):
            label += f" (with {archetype['secondary']} as modifier)"
        lines.append(f"**{label}**")
        if archetype.get("evidence"):
            lines.append(f"_{archetype['evidence']}_")
    else:
        lines.append("_Not yet completed_")
    lines.append("")

    # Business model
    lines += ["## Business Model", ""]
    lines.append(_field(brief.get("business_model")))
    lines.append("")

    # Competitor insight
    lines += ["## Competitor Insight", ""]
    lines.append(_field(brief.get("competitor_insight")))
    lines.append("")

    # Comparable newsletter
    lines += ["## Comparable Newsletter", ""]
    lines.append(_field(brief.get("comparable_newsletter")))
    lines.append("")

    return "\n".join(lines)
