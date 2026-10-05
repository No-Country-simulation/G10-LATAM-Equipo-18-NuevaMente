"""
test_robustness_pipeline.py

Purpose:
    Unit tests for GroqClient resiliency (Tenacity retries and Pydantic structured output).
    All external API calls are mocked via unittest.mock.

Input:
    N/A - uses mocked Groq client.

Output:
    pytest assertions validating retry logic and structured generation.
"""

import pytest
from pydantic import BaseModel, Field
from unittest.mock import patch, MagicMock
from app.infrastructure.llm.groq_client import GroqClient
from app.services.markdown_splitter_adapter import RobustMarkdownSplitter
from groq import APIConnectionError


class MockEducationalResponse(BaseModel):
    title: str = Field(description="Topic title")
    concepts: list[str] = Field(description="Key concepts")


@patch("app.infrastructure.llm.groq_client.groq.Client")
def test_groq_client_structured_output(mock_groq_client):
    """Validates that GroqClient correctly processes Pydantic structured outputs."""
    mock_instance = MagicMock()
    mock_groq_client.return_value = mock_instance

    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"title": "OCI Networks", "concepts": ["VCN", "Subnets"]}'
    mock_instance.chat.completions.create.return_value = mock_response

    client = GroqClient(api_key="real_looking_key")
    result = client.generate_structured("Generate a summary about OCI", MockEducationalResponse)

    assert isinstance(result, MockEducationalResponse)
    assert result.title == "OCI Networks"
    assert "VCN" in result.concepts


@patch("app.infrastructure.llm.groq_client.groq.Client")
def test_groq_client_retry_on_rate_limit(mock_groq_client):
    """Validates Tenacity retry on transient connection errors before success."""
    mock_instance = MagicMock()
    mock_groq_client.return_value = mock_instance

    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"title": "Success", "concepts": []}'

    # Fail on first attempt, succeed on second
    mock_instance.chat.completions.create.side_effect = [
        APIConnectionError(request=MagicMock()),
        mock_response,
    ]

    client = GroqClient(api_key="real_looking_key")
    result = client.generate_structured("Test prompt", MockEducationalResponse)

    assert result.title == "Success"
    assert mock_instance.chat.completions.create.call_count == 2


def test_markdown_splitter():
    """Validates that RobustMarkdownSplitter preserves heading metadata."""
    markdown_text = (
        "# Cloud Architecture\n\nCloud introduction.\n\n"
        "## Oracle VCN\n\nVCNs are virtual networks."
    )
    splitter = RobustMarkdownSplitter(child_chunk_size=100)
    chunks = splitter.split_document(markdown_text)

    assert len(chunks) == 2
    assert "Header_1" in chunks[0]["metadata"]
    assert chunks[0]["metadata"]["Header_1"] == "Cloud Architecture"
    assert "Header_2" in chunks[1]["metadata"]
    assert chunks[1]["metadata"]["Header_2"] == "Oracle VCN"
    assert "virtual networks" in chunks[1]["content"]
