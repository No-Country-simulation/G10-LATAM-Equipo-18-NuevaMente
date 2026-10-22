# Orquestación multi-agente (LangGraph)

> `docs/04-Documentacion/backend/architecture/` · [Volver al README](../../../../README.md)

Este documento explica cómo NuevaMente organiza la generación de contenido como
un **grafo de agentes especializados**. Es la referencia del orquestador
(`app/services/langgraph_orchestrator.py`) y de las piezas que lo rodean: el
router de proveedores, el planificador de cobertura y la cascada de modelos.

Si solo quieres entender el mecanismo de fidelidad, empieza por
[Anclaje de fuentes](../../../01-Arquitectura/Anclaje_de_Fuentes.md) y luego
consulta [Anclaje técnico](../quality/Anclaje_Tecnico.md).

---

## 1. La idea en simple

Generar 20 flashcards no es una sola llamada al modelo. Es una cadena de tareas
que deben ejecutarse en orden y, a veces, repetirse:

1. Mirar el documento y decidir **qué temas** cubrir.
2. **Redactar** los elementos por lotes.
3. **Limpiar** duplicados.
4. **Verificar** que cada elemento esté respaldado por el texto original.
5. **Auditar** la calidad pedagógica.
6. **Reparar** o **completar** lo que falló.
7. **Formatear** y guardar la respuesta.

Cada tarea es un **nodo** del grafo. El nodo recibe un estado compartido, hace su
trabajo y devuelve solo los campos que modificó. LangGraph se encarga de pasar
ese estado de un nodo al siguiente.

```text
                    ┌──────────┐
                    │ planner  │
                    └────┬─────┘
                         ▼
                    ┌──────────┐
                    │  writer  │
                    └────┬─────┘
                         ▼
                    ┌─────────────┐
                    │ deduplicator│
                    └─────┬───────┘
                          ▼
                    ┌───────────────────┐
                    │ grounding_verifier│
                    └─────────┬─────────┘
                              ▼
                    ┌──────────────────┐
                    │      critic      │
                    └────────┬─────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
   ┌────────┐          ┌─────────┐          ┌──────────┐
   │ repair │          │ refiner │          │ formatter│
   └───┬────┘          └────┬────┘          └────┬─────┘
       └────────────────────┴────────────────────┘
                                                 ▼
                                                END
```

---

## 2. Piezas del sistema

| Pieza | Archivo | Rol |
| :--- | :--- | :--- |
| **Orquestador** | `app/services/langgraph_orchestrator.py` | Define el grafo, el estado y los 8 nodos. |
| **Etapas reutilizables** | `app/services/pipeline_stages.py` | Implementación de generación por lotes, deduplicación, verificación, crítica, reparación y formateo. |
| **Router de proveedores** | `app/services/multi_agent_router.py` | Elige el proveedor preferido por formato y su orden de respaldo. |
| **Planificador de cobertura** | `app/services/coverage_planner.py` | Decide cuántos elementos puede sostener el documento y cómo repartirlos por sección. |
| **Rate guard** | `app/services/rate_guard.py` | Evita reintentos inútiles sobre proveedores en cuota o caídos. |
| **Prompts** | `app/prompts/` | Instrucciones de planificador, writer, formatos y auditor. |
| **Trazado opcional** | `app/core/timer.py` (`PipelineTracer`) | Mide etapas y llamadas al LLM cuando el llamador lo inyecta. |
| **Entrada HTTP** | `app/api/v1/endpoints/documents.py` | Recupera contexto y expone el grafo como JSON o como stream SSE. |

---

## 3. Estado compartido (`AgentState`)

`AgentState` es un `TypedDict` que viaja entre nodos. Se agrupa en:

| Grupo | Campos principales |
| :--- | :--- |
| **Entrada** | `request`, `doc_title`, `target_language`, `top_passages`, `all_parent_chunks`, `key_concepts`, `prerequisites`, `document_id`, `prompt_hash` |
| **Planificación** | `coverage_plan`, `target_quantity`, `effective_target`, `capacity_warning`, `topics` |
| **Generación** | `raw_items`, `dedup_items`, `verified_items` |
| **Auditoría** | `evaluation`, `audited_items`, `preliminary_score` |
| **Bucle de mejora** | `revision_count`, `max_revisions`, `repaired_indices` |
| **Salida** | `nodes_executed`, `final_items`, `final_response` |

Cada nodo devuelve **solo sus claves**; LangGraph las fusiona con el estado
anterior. Por eso un nodo no necesita conocer el orden completo del grafo.

---

## 4. Los 8 nodos

### 4.1 `planner`

- **Entrada:** solicitud, todos los *parent chunks*, conceptos clave.
- **Qué hace:** `CoveragePlanner().plan(...)` calcula la capacidad real del
  documento y la estrategia de reparto; `_stage_planner()` convierte el plan en
  tópicos con fragmentos y `chunk_id` citables.
- **Salida:** `coverage_plan`, `target_quantity`, `effective_target`,
  `capacity_warning`, `topics`.

### 4.2 `writer`

- **Entrada:** tópicos, pasajes RAG, objetivo efectivo.
- **Qué hace:** `_stage_batch_generators()` redacta por lotes. Elige la plantilla
  del formato en `app/prompts/formats/` y recorre la **cascada de modelos** del
  formato hasta que un proveedor responda.
- **Salida:** `raw_items`.

Casos especiales dentro del writer:

- **Resumen ejecutivo:** se genera en una sola pasada sobre todo el documento
  (`_generate_summary_items`), con rondas adicionales si faltan puntos.
- **Lotes pequeños (≤ 10 elementos y varios tópicos):** se consolidan los
  tópicos en una sola llamada para no fragmentar el contexto.

### 4.3 `deduplicator`

- **Qué hace:** `_stage_deduplicate()` compara textos con
  `difflib.SequenceMatcher` y descarta elementos con similitud ≥ `0.88`.
- **Salida:** `dedup_items`.

### 4.4 `grounding_verifier`

- **Qué hace:** `_stage_verify_grounding()` resuelve cada `chunk_id` citado y
  marca `fuentes[i].verificado`.
- **Salida:** `verified_items` (cada elemento con `grounded = any(verificado)`).

Las reglas exactas y sus umbrales están en
[Anclaje técnico](../quality/Anclaje_Tecnico.md).

### 4.5 `critic`

- **Qué hace:** `_evaluate_quality_with_critic()` envía cada elemento y sus
  fuentes citadas al auditor LLM (`app/prompts/auditor.md`), usando
  `settings.CRITIC_CASCADE`.
- **Salida:** `evaluation` (`QualityEvaluation`), `audited_items`,
  `preliminary_score`.

Si ningún proveedor del crítico responde, se usa una evaluación heurística y el
grafo continúa.

### 4.6 `repair`

- **Qué hace:** reescribe en un solo lote los elementos sin fuente verificada o
  con claridad `Baja`/`Low`, vuelve a verificar su anclaje y **re-audita** solo
  esos elementos para no arrastrar el veredicto anterior.
- **Garantía anti-bucle:** cada índice se registra en `repaired_indices` y no se
  repara dos veces.
- **Salida:** `audited_items` actualizados, `repaired_indices`,
  `revision_count + 1`.

### 4.7 `refiner`

- **Qué hace:** si faltan elementos para llegar al objetivo, pide más usando
  tópicos o pasajes aún no explotados (`_stage_completion`).
- **Salida:** `audited_items` ampliados, `revision_count + 1`.

### 4.8 `formatter`

- **Qué hace:** descarta elementos basura o marcadores de relleno, aplica el
  límite de elementos, calcula el score final, guarda el artefacto en storage,
  genera el PDF si aplica y arma la respuesta.
- **Salida:** `final_items`, `final_response` (`AdaptationResponse`).

---

## 5. Router y cascadas de modelos

`MultiAgentRouter` tiene dos responsabilidades:

1. **Proveedor preferido por formato** (`route_task`):
   - Flashcards y quiz → `groq`.
   - Tutorial → `gemini`.
   - Resumen ejecutivo y guion de clase → `openrouter`.
   - Sin coincidencia → `gemini`.
2. **Orden de respaldo** (`get_model_cascade`): lee `settings.LLM_CASCADES` y,
   si no encuentra el formato, prueba con la clave canónica
   (`executive_summary`, `class_script`, …). Si tampoco hay cascada, usa
   `get_cascade_order()` (solo proveedores, sin modelo fijo).

Cada entrada de la cascada es `{"provider": ..., "model": ...}`. Antes de
intentar una llamada:

- se descarta el proveedor si su cliente no está disponible;
- `LlmRateGuard.should_attempt()` evita reintentar un proveedor castigado;
- `LlmRateGuard.wait_for_slot()` aplica la espera de cuota;
- un éxito limpia el estado del proveedor; un fallo lo penaliza.

Cuando el proveedor principal falla, el writer simplemente pasa a la siguiente
entrada de la cascada, sin intervención del usuario. `last_provider` y
`last_model` quedan registrados y se reflejan en la respuesta
(`proveedor_llm`, `modelo_llm`, `modelos_usados`).

---

## 6. Cobertura y cantidad

`CoveragePlanner` evita el problema clásico de "pedir 50 tarjetas a un párrafo".
Primero filtra fragmentos sustantivos, agrupa por sección y estima la capacidad:

- `min_chars_per_item`: 50 (flashcards), 80 (quiz), 120 (otros formatos);
- la petición solo se recorta si es **desproporcionada** y el documento tiene
  menos de 800 caracteres de contenido;
- si se recorta, se genera un `capacity_warning` que viaja al frontend.

Estrategias de reparto:

| Estrategia | Formatos | Comportamiento |
| :--- | :--- | :--- |
| `distributed` | flashcards, quiz | Reparte los elementos proporcionalmente al volumen de cada sección (mínimo 1 por sección). |
| `sequential` | tutorial, guion de clase | Mantiene el orden del documento (los formatos con secuencia pedagógica). |
| `holistic` | resumen ejecutivo | Agrega todo el documento en una sección sintética con extractos citables. |

La cantidad objetivo se resuelve con `QUANTITY_TABLE` (por formato y nivel
`breve`/`estandar`/`amplio`/`exhaustivo`), salvo que el cliente envíe
`cantidad_objetivo`. El objetivo final es
`min(requested, coverage_plan.viable_target)`.

---

## 7. Bucle de auto-corrección

Tras el crítico, `_should_refine_or_complete()` decide la rama con esta
prioridad:

1. **`repair`** — hay elementos sin fuente verificada o con claridad baja, no se
   repararon aún y `revision_count < LANGGRAPH_MAX_REVISIONS`.
2. **`refiner`** — faltan elementos para el objetivo y queda presupuesto.
3. **`formatter`** — calidad aprobada o presupuesto agotado.

`LANGGRAPH_MAX_REVISIONS` (default `2`) limita cuántas vueltas puede dar el
bucle. `repaired_indices` impide reparar el mismo elemento dos veces.

Si tras reparar un elemento sigue sin respaldo, se descarta; el hueco se repone
con `refiner` (o con una nueva petición al modelo en el caso del resumen
ejecutivo, que nunca usa contenido de relleno).

---

## 8. Entradas públicas y streaming

| Método | Uso |
| :--- | :--- |
| `run_pipeline(...)` | Ejecuta el grafo completo y devuelve `AdaptationResponse` (JSON). |
| `iter_pipeline(...)` | Ejecuta el grafo y emite un evento por nodo; lo usa el SSE de `POST /documents/{id}/adapt`. |

Eventos del stream: `retrieval`, `planner`, `writer`, `deduplicator`,
`grounding_verifier`, `critic`, `refiner`, `formatter`, y finalmente
`done` (con la respuesta) o `failed`.

**Caché de respuestas:** `_compute_request_hash()` combina título, primeros 1000
caracteres del contenido, perfil, formato, nicho, nivel de detalle, cantidad e
idioma. Si el hash ya existe y `forzar_regenerar` es falso, se devuelve la
respuesta cacheada con `origen = "cache"`.

---

## 9. Qué devuelve el grafo

`AdaptationResponse` incluye, además del contenido y la evaluación de calidad,
metadatos de orquestación:

| Campo (alias) | Significado |
| :--- | :--- |
| `orquestacion_grafo` | `True` cuando la respuesta la produjo el grafo. |
| `nodos_grafo_ejecutados` | Nodos que realmente se ejecutaron, en orden. |
| `revisiones_grafo` | Vueltas del bucle de reparación/refinamiento. |
| `items_reparados` | Índices de los elementos reescritos. |
| `proveedor_llm` / `modelo_llm` | Último proveedor que generó contenido. |
| `proveedor_critico` / `modelo_critico` | Proveedor que hizo la auditoría. |
| `modelos_usados_detalle` | Todos los modelos que participaron. |
| `origen` | `llm` o `cache`. |
| `timings` / `llm_calls` | Telemetría cuando se inyecta un `PipelineTracer`. |

---

## 10. Configuración relacionada

| Ajuste | Default | Efecto |
| :--- | :--- | :--- |
| `LANGGRAPH_MAX_REVISIONS` | `2` | Vueltas máximas de reparación/refinamiento. |
| `MAX_TOP_K_CHUNKS` | `5` | Pasajes RAG iniciales. |
| `RAG_CONTEXT_SNIPPET_SIZE` | `1500` | Caracteres de cada fragmento entregado al modelo. |
| `DEFAULT_OUTPUT_LANGUAGE` | `Spanish` | Idioma por defecto si la solicitud no lo indica. |
| `LLM_CASCADES` | Por formato | Cascadas `(proveedor, modelo)`. |
| `CRITIC_CASCADE` | Groq → Gemini → OpenRouter | Cadena del auditor. |

> Los identificadores de modelo son constantes de `config.py`; se cambian
> editando el archivo, no con `.env`.

---

## 11. Pruebas

```bash
cd backend
uv run --with pytest --with email-validator --with genanki pytest tests/test_langgraph_orchestrator.py tests/test_grounding_verification.py tests/test_score_lifecycle.py
```

Cubren la construcción del grafo, el contrato de la respuesta, el ciclo del
score y la invalidación de veredictos tras reparar.

---

## 12. Limitaciones conocidas

- El grafo es **secuencial con una bifurcación condicional de tres destinos**
  (`repair`, `refiner`, `formatter`); no hay ejecución paralela de nodos.
- El `PipelineTracer` existe pero los endpoints no lo inyectan por defecto: la
  telemetría detallada solo aparece si el llamador lo pasa.
- El caché es **en memoria por proceso**: se pierde al reiniciar y no se comparte
  entre workers.
- La calidad del resultado depende de la cascada disponible; si todos los
  proveedores del writer fallan, se generan elementos de relleno marcados como
  `es_fallback`, que el formatter descarta.

---

<div align="right">

[Volver al README](../../../../README.md)

</div>
