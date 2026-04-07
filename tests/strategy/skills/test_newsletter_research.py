from unittest.mock import patch, MagicMock
from agents.strategy.skills.newsletter_research import run_newsletter_research

def test_run_newsletter_research_returns_dict():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='''{
        "competitors": [
            {
                "name": "The Hustle",
                "platform": "Beehiiv",
                "estimated_subscribers": "2M+",
                "positioning": "Business and tech news for entrepreneurs",
                "content_format": "Daily digest",
                "monetisation": "Sponsorships",
                "gaps": "Does not cover personal finance for early-career professionals"
            }
        ],
        "gap_analysis": "No newsletter serves early-career professionals making their first investment decisions with actionable weekly guidance.",
        "niche_depth_recommendation": "Go deeper into first-time investor territory — the broad personal finance space is saturated."
    }''')]

    with patch("agents.strategy.skills.newsletter_research.anthropic.Anthropic") as MockClient:
        mock_client = MockClient.return_value
        mock_client.messages.create.return_value = mock_response
        result = run_newsletter_research(niche_candidate="personal finance for millennials")

    assert "competitors" in result
    assert "gap_analysis" in result
    assert "niche_depth_recommendation" in result
    assert isinstance(result["competitors"], list)
