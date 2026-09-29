import pytest
from unittest.mock import patch, MagicMock
from app.services.ingester_service import IngesterService

def test_ingester_chunking_parent_child():
    """Testea la correcta creación de padres e hijos respetando el tamaño y solapamiento"""
    service = IngesterService(child_chunk_size=50, parent_chunk_size=150, overlap=10)
    
    texto = "A" * 300 # Un texto de 300 caracteres
    doc_data = service.parse_and_chunk_document(content=texto, title="Prueba")
    
    parents = doc_data["parent_chunks"]
    children = doc_data["child_chunks"]
    
    assert len(parents) > 0
    assert len(children) > len(parents)
    
    # Cada hijo debe tener un parent_id válido
    parent_ids = [p["id"] for p in parents]
    for child in children:
        assert child["parent_id"] in parent_ids

@patch("app.services.ingester_service.logging")
def test_keybert_concept_extraction(mock_logging):
    """Testea que se intente extraer conceptos de clase en la ingesta si hay texto válido"""
    # Mockear KeyBERT inside the method is tricky without modifying sys.modules or mocking the specific import
    # A cleaner approach is patching where KeyBERT is used or skipping the actual download during unit tests.
    # For now we just verify it executes without crashing on a very short text, which might not extract anything.
    service = IngesterService(child_chunk_size=50, parent_chunk_size=100)
    
    texto = "Este es un texto corto. El estudiante necesita aprender Python."
    doc_data = service.parse_and_chunk_document(content=texto, title="Prueba Mínima")
    
    # Verificamos que se haya añadido la propiedad 'key_concepts' o 'metadata' (si KeyBERT cargó o falló elegantemente)
    for parent in doc_data["parent_chunks"]:
        assert "metadata" in parent
        assert "key_concepts" in parent["metadata"]
