import json
import re
import anthropic

SYSTEM_PROMPT = """You are a newsletter competitive intelligence specialist. Your scope is newsletters ONLY — this includes individual creator newsletters, company newsletters, media newsletters, and any regular editorial publication.

Do NOT include YouTube channels, podcasts, Reddit communities, or social media accounts.

For a given niche, you will:
1. Research active newsletters in the space
2. For each significant newsletter, map: name, platform, estimated subscribers (if findable), positioning frame, content format, monetisation model, and what they consistently miss
3. Produce a gap analysis: what is not being covered, which reader needs are unmet, what positioning frames are unclaimed
4. Give a niche depth recommendation based purely on what you find — if the space is uncrowded, say so; if dense, recommend going deeper and name specific directions

Return ONLY a JSON object with these exact keys:
{
  "competitors": [
    {
      "name": "string",
      "platform": "string",
      "estimated_subscribers": "string",
      "positioning": "string",
      "content_format": "string",
      "monetisation": "string",
      "gaps": "string"
    }
  ],
  "gap_analysis": "string",
  "niche_depth_recommendation": "string"
}"""


def run_newsletter_research(niche_candidate: str) -> dict:
    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Research the newsletter landscape for this niche: {niche_candidate}\n\nReturn the JSON object.",
            }
        ],
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    data = json.loads(raw.strip())
    required = {"competitors", "gap_analysis", "niche_depth_recommendation"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Model response missing required keys: {missing}")
    return data
