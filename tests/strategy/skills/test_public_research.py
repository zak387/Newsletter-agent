import pytest
from unittest.mock import patch, MagicMock
from agents.strategy.skills.public_research import run_public_research

def test_run_public_research_returns_dict():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='''{
        "content_summary": "Creator posts about personal finance for millennials",
        "audience_signals": ["25-35 age range", "urban professionals"],
        "gaps_flagged": ["no survey data available"],
        "category_suggestion": "Personal transformation",
        "sub_niches": ["financial independence", "career transitions", "mindset"]
    }''')]

    with patch("agents.strategy.skills.public_research.anthropic.Anthropic") as MockClient:
        mock_client = MockClient.return_value
        mock_client.messages.create.return_value = mock_response
        result = run_public_research(
            urls=["https://twitter.com/example"],
            human_context="Engagement rate around 4%",
        )

    assert "content_summary" in result
    assert "sub_niches" in result
    assert isinstance(result["sub_niches"], list)
