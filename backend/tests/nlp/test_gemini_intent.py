"""Unit tests for Gemini intent extraction and configuration."""
import pytest
from unittest.mock import AsyncMock, patch
import httpx

from app.core.config import get_settings
from app.nlp.intent import parse_intent


@pytest.mark.asyncio
async def test_gemini_intent_parser_mock():
    mock_gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": """{
                                "category": "laptop",
                                "budget_max": 75000,
                                "currency": "INR",
                                "use_cases": ["coding", "gaming"],
                                "requirements": ["16GB RAM", "RTX 3050"],
                                "preferred_brands": ["ASUS"],
                                "clean_provider_query": "ASUS gaming laptop 16GB RAM"
                            }"""
                        }
                    ]
                }
            }
        ]
    }

    mock_resp = httpx.Response(
        status_code=200,
        json=mock_gemini_response,
        request=httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/models/test:generateContent"),
    )

    settings = get_settings()
    orig_token = settings.gemini_api_key
    settings.gemini_api_key = "test-gemini-token"

    try:
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            intent = await parse_intent("best ASUS gaming laptop under 75000 for coding with 16GB RAM", country="IN", currency="INR")
            assert intent.parser == "gemini"
            assert intent.category == "laptop"
            assert intent.budget.max == 75000.0
            assert "coding" in intent.use_cases
            assert "16GB RAM" in intent.requirements
            assert "ASUS" in intent.preferred_brands
            assert intent.provider_query == "ASUS gaming laptop 16GB RAM"
    finally:
        settings.gemini_api_key = orig_token
