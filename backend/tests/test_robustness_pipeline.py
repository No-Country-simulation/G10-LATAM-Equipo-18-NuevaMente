import pytest
from pydantic import BaseModel, Field
from unittest.mock import patch, MagicMock
from app.infrastructure.llm.groq_adapter import GroqAdapter
from app.services.markdown_splitter_adapter import RobustMarkdownSplitter
from groq import APIConnectionError

# Esquema de prueba
class MockEducationalResponse(BaseModel):
    title: str = Field(description="Título del tema")
    concepts: list[str] = Field(description="Conceptos clave")

@patch("app.infrastructure.llm.groq_adapter.groq.Client")
def test_groq_adapter_structured_output(mock_groq_client):
    """Prueba que el GroqAdapter procesa correctamente las salidas estructuradas"""
    
    # Configuramos el mock para simular la respuesta de Groq
    mock_instance = MagicMock()
    mock_groq_client.return_value = mock_instance
    
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"title": "Redes OCI", "concepts": ["VCN", "Subnets"]}'
    mock_instance.chat.completions.create.return_value = mock_response

    adapter = GroqAdapter(api_key="mock_key")
    result = adapter.generate_structured("Genera un resumen sobre OCI", MockEducationalResponse)
    
    assert isinstance(result, MockEducationalResponse)
    assert result.title == "Redes OCI"
    assert "VCN" in result.concepts

@patch("app.infrastructure.llm.groq_adapter.groq.Client")
def test_groq_adapter_retry_on_rate_limit(mock_groq_client):
    """Prueba la resiliencia (tenacity retry) ante un fallo temporal simulado"""
    mock_instance = MagicMock()
    mock_groq_client.return_value = mock_instance
    
    # Hacemos que falle la primera vez y funcione la segunda
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"title": "Éxito", "concepts": []}'
    
    mock_instance.chat.completions.create.side_effect = [
        APIConnectionError(request=MagicMock()), 
        mock_response
    ]

    adapter = GroqAdapter(api_key="mock_key")
    result = adapter.generate_structured("Prueba", MockEducationalResponse)
    
    assert result.title == "Éxito"
    assert mock_instance.chat.completions.create.call_count == 2

def test_markdown_splitter():
    """Prueba que el MarkdownHeaderTextSplitter preserva los metadatos de los subtítulos"""
    markdown_text = "# Arquitectura Cloud\n\nIntroducción a la nube.\n\n## Oracle VCN\n\nLas VCN son redes virtuales."
    splitter = RobustMarkdownSplitter(child_chunk_size=100)
    chunks = splitter.split_document(markdown_text)
    
    assert len(chunks) == 2
    assert "Header_1" in chunks[0]["metadata"]
    assert chunks[0]["metadata"]["Header_1"] == "Arquitectura Cloud"
    
    assert "Header_2" in chunks[1]["metadata"]
    assert chunks[1]["metadata"]["Header_2"] == "Oracle VCN"
    # El contenido de la sección VCN
    assert "redes virtuales" in chunks[1]["content"]
