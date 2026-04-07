import json
import re
import anthropic

SYSTEM_PROMPT = """You are a niche timing and trend analyst. You assess whether a newsletter niche is well-timed, growing, or saturating.

For a given niche you will:
1. Assess search volume trajectory (growing / flat / declining)
2. Identify cultural, regulatory, or consumer behaviour tailwinds
3. Flag saturation signals or declining interest where present
4. Give a plain-language timing verdict
5. Assess purchasing power signals for the audience

Purchasing power is CONFIRMED if at least two of these signals are present:
- Creator has successfully affiliated with or sponsored products above a meaningful price point
- Creator's audience has responded to paid offers
- Survey data indicates disposable income or premium purchase behaviour
- The niche itself implies above-average spend

Return ONLY a JSON object with these exact keys:
{
  "search_trajectory": "string",
  "tailwinds": ["string"],
  "saturation_signals": ["string"],
  "timing_verdict": "string",
  "purchasing_power_signals": ["string"],
  "purchasing_power_confirmed": true or false
}"""


def run_trend_research(niche_candidate: str, creator_context: str = "") -> dict:
    client = anthropic.Anthropic()

    context_block = f"\nCreator context for purchasing power assessment:\n{creator_context}" if creator_context else ""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Assess niche timing and purchasing power for: {niche_candidate}{context_block}\n\nReturn the JSON object.",
            }
        ],
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    data = json.loads(raw.strip())
    required = {"search_trajectory", "tailwinds", "saturation_signals", "timing_verdict", "purchasing_power_signals", "purchasing_power_confirmed"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Model response missing required keys: {missing}")
    # Coerce purchasing_power_confirmed to bool in case model returns a string
    data["purchasing_power_confirmed"] = bool(data["purchasing_power_confirmed"])
    return data
