"""
Verification test script for the recent fixes.
"""
from app.infrastructure.llm.groq_client import GroqClient
from app.infrastructure.llm.openrouter_client import OpenRouterClient
from app.schemas.adaptation import RagFuente
from app.services.agent_orchestrator import AgentOrchestrator, _is_spanish
from app.services.coverage_planner import CoveragePlanner
from app.services.noise_filter_service import NoiseFilter

# 1. Test RagFuente default score
rf = RagFuente(chunk_id="c1", extracto="test")
assert rf.similitud_score is None, f"Expected None, got {rf.similitud_score}"
print("RagFuente check: OK")

# 2. Test _is_spanish
assert _is_spanish("Spanish") is True
assert _is_spanish("spanish") is True
assert _is_spanish("Español") is True
assert _is_spanish("es") is True
assert _is_spanish("English") is False
assert _is_spanish("en") is False
assert _is_spanish(None) is True
print("_is_spanish check: OK")

# 3. Test _parse_json_batch with both array and wrapped object
orch = AgentOrchestrator()
arr = orch._parse_json_batch('[{"pregunta": "Q1"}]')
assert arr == [{"pregunta": "Q1"}], f"Array parse failed: {arr}"
obj = orch._parse_json_batch('{"items": [{"pregunta": "Q2"}]}')
assert obj == [{"pregunta": "Q2"}], f"Object parse failed: {obj}"
print("_parse_json_batch check: OK")

# 4. Test CoveragePlanner noise filtering with '5 Licencia'
cp = CoveragePlanner()
chunks = [
    {"title": "5 Licencia", "content": "Esta página forma parte del curso bajo licencia Creative Commons Reconocimiento-NoComercial..."},
    {"title": "1. Fundamentos", "content": "A" * 200}
]
substantive = cp._filter_substantive(chunks)
assert len(substantive) == 1 and substantive[0]["title"] == "1. Fundamentos", f"Expected only Fundamentos, got: {substantive}"
print("CoveragePlanner noise filtering check: OK")

print("ALL TESTS PASSED SUCCESSFULLY!")
