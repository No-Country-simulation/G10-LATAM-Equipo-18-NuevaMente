"""
timer.py

Módulo de trazabilidad e instrumentación de tiempos y llamadas API para NuevaMente Backend.
Permite medir con precisión en milisegundos la duración de cada etapa del pipeline de adaptación,
así como registrar las llamadas a LLM, embeddings y eventos de cuota/retries.
"""

import time
from typing import Dict, Any, Optional

class PipelineTracer:
    def __init__(self):
        self.start_time = time.time()
        self.timings: Dict[str, float] = {}
        self.llm_calls: Dict[str, Any] = {
            "planificar": 0,
            "generar": 0,
            "verificar": 0,
            "embeddings_llamadas": 0,
            "embeddings_chunks_total": 0,
            "embeddings_chunks_cache": 0,
            "tokens_estimados": 0,
            "retries_429": 0,
            "espera_429_s": 0.0
        }
        self._stage_starts: Dict[str, float] = {}

    def start_stage(self, stage_name: str) -> None:
        self._stage_starts[stage_name] = time.time()

    def end_stage(self, stage_name: str) -> float:
        start = self._stage_starts.pop(stage_name, time.time())
        elapsed_ms = round((time.time() - start) * 1000, 2)
        self.timings[stage_name] = round(self.timings.get(stage_name, 0.0) + elapsed_ms, 2)
        return elapsed_ms

    def record_llm_call(self, call_type: str, tokens: int = 0) -> None:
        if call_type in self.llm_calls:
            self.llm_calls[call_type] += 1
        else:
            self.llm_calls[call_type] = 1
        self.llm_calls["tokens_estimados"] += tokens

    def record_embedding_call(self, chunks_count: int, from_cache: int = 0) -> None:
        self.llm_calls["embeddings_llamadas"] += 1
        self.llm_calls["embeddings_chunks_total"] += chunks_count
        self.llm_calls["embeddings_chunks_cache"] += from_cache

    def record_429_retry(self, wait_seconds: float) -> None:
        self.llm_calls["retries_429"] += 1
        self.llm_calls["espera_429_s"] = round(self.llm_calls["espera_429_s"] + wait_seconds, 2)

    def total_elapsed_ms(self) -> float:
        return round((time.time() - self.start_time) * 1000, 2)
