import json
import re
import anthropic

SYSTEM_PROMPT = """You are a creator research specialist. Your job is to audit a creator's public content and extract signals about their niche, audience, and positioning.

You will be given URLs to the creator's public content and any human-supplied context. Read what is available and extract:
- A summary of the creator's content focus
- Audience signals (age, profession, interests, purchasing behaviour)
- Gaps you could not confirm from the available data
- A suggested primary category (Jobs / Hobbies / Investments / Personal transformation)
- All plausible sub-niches visible in the content

Return ONLY a JSON object with these exact keys:
{
  "content_summary": "string",
  "audience_signals": ["string"],
  "gaps_flagged": ["string"],
  "category_suggestion": "string",
  "sub_niches": ["string"]
}"""


def run_public_research(urls: list[str], human_context: str = "") -> dict:
    client = anthropic.Anthropic()

    url_list = "\n".join(f"- {u}" for u in urls) if urls else "No URLs provided."
    context_block = f"\nHuman-supplied context:\n{human_context}" if human_context else ""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Creator content URLs:\n{url_list}{context_block}\n\nPlease audit this creator's public content and return the JSON object.",
            }
        ],
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    data = json.loads(raw.strip())
    required = {"content_summary", "audience_signals", "gaps_flagged", "category_suggestion", "sub_niches"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Model response missing required keys: {missing}")
    return data
