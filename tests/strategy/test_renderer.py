from agents.strategy.renderer import render_brief

def test_render_includes_all_sections():
    brief = {
        "newsletter_name": ["The Long Game", "Signal vs Noise", "Compound Weekly"],
        "newsletter_name_rationale": ["Reflects compounding growth", "Cuts through clutter", "Weekly cadence + value"],
        "niche_umbrella": "Personal transformation > mindset + longevity for high-performers",
        "niche_rationale": "Competitor landscape is thin above surface-level productivity content",
        "target_reader": "A 34-year-old operations manager who reads widely but acts rarely.",
        "newsletter_statement": "This newsletter helps high-performers achieve sustainable output by applying systems thinking to personal health.",
        "why_exist": "Search interest in burnout recovery has grown 40% YoY. No newsletter owns this frame for professionals.",
        "why_creator": "Spent 3 years recovering from adrenal fatigue while running a team of 12. Built the system she wished existed.",
        "content_pillars": [
            {"name": "The Protocol", "description": "Evidence-based recovery and performance routines"},
            {"name": "The Mistake", "description": "What high-performers get wrong and the fix"},
            {"name": "The Read", "description": "One curated resource per week with a contrarian take"},
        ],
        "creator_archetype": {"primary": "Experimenter", "secondary": "Expert", "evidence": "Publishes weekly self-experiments with tracked outcomes"},
        "business_model": "Affiliates only (under 5k subscribers)",
        "competitor_insight": "No newsletter in this space pairs recovery science with operational thinking. Most competitors are either too clinical or too motivational.",
        "comparable_newsletter": "Dan Go's High Performance Founder — similar reader but focused on physical performance, not recovery systems.",
    }
    md = render_brief(brief)
    assert "## Newsletter Name" in md
    assert "The Long Game" in md
    assert "## Target Reader" in md
    assert "## Newsletter Statement" in md
    assert "## Content Pillars" in md
    assert "## Creator Archetype" in md
    assert "## Business Model" in md
    assert "## Competitor Insight" in md

def test_render_blank_field_shows_note():
    brief = {
        "newsletter_name": None,
        "newsletter_name_rationale": None,
        "niche_umbrella": None,
        "niche_rationale": None,
        "target_reader": None,
        "newsletter_statement": None,
        "why_exist": None,
        "why_creator": None,
        "content_pillars": None,
        "creator_archetype": None,
        "business_model": None,
        "competitor_insight": None,
        "comparable_newsletter": None,
    }
    md = render_brief(brief)
    assert "_Not yet completed_" in md
