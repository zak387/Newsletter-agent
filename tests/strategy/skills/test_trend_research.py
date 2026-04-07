from unittest.mock import patch, MagicMock
from agents.strategy.skills.trend_research import run_trend_research

def test_run_trend_research_returns_dict():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='''{
        "search_trajectory": "Growing — 35% increase in search volume over 24 months",
        "tailwinds": ["Rising interest rates making savings accounts attractive again", "Gen Z entering workforce with student debt concerns"],
        "saturation_signals": ["Several well-funded newsletters launched in 2023"],
        "timing_verdict": "Good timing if differentiated — market is growing but filling up fast",
        "purchasing_power_signals": ["Niche implies above-average financial engagement"],
        "purchasing_power_confirmed": true
    }''')]

    with patch("agents.strategy.skills.trend_research.anthropic.Anthropic") as MockClient:
        mock_client = MockClient.return_value
        mock_client.messages.create.return_value = mock_response
        result = run_trend_research(
            niche_candidate="personal finance for millennials",
            creator_context="Has sold a $97 budgeting course to 200 buyers",
        )

    assert "search_trajectory" in result
    assert "purchasing_power_confirmed" in result
    assert isinstance(result["purchasing_power_confirmed"], bool)
