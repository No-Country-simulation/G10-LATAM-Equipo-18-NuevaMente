# Anclaje técnico (verificación de fidelidad RAG)

> `docs/04-Documentacion/backend/quality/` · [Volver al README](../../../../README.md)

Referencia de implementación del mecanismo de **anclaje** descrito en
[Anclaje de fuentes](../../../01-Arquitectura/Anclaje_de_Fuentes.md). Está
dirigida a quien mantiene el pipeline de generación; asume familiaridad con el
orquestador LangGraph y con los esquemas Pydantic.

---

## 1. Dónde vive el código

| Pieza | Archivo | Rol |
| :--- | :--- | :--- |
| Verificación léxica | `app/services/pipeline_stages.py` → `_stage_verify_grounding()` | Comprueba que cada `chunk_id` citado exista y que el extracto esté respaldado. |
| Nodo del grafo | `app/services/langgraph_orchestrator.py` → `_node_grounding_verifier()` | Ejecuta la etapa anterior y reporta el progreso `verificacion_anclaje`. |
| Auditoría del crítico | `app/services/pipeline_stages.py` → `_stage_critic()` | Un LLM audita cada elemento contra las fuentes citadas. |
| Reparación | `app/services/langgraph_orchestrator.py` → `_node_repair()` | Reescribe los elementos no verificados y re-audita. |
| Cálculo del score | `app/services/langgraph_orchestrator.py` (bloque posterior a `_format_adapted_content`) | Combina ambos veredictos y escribe `source_grounding_score`. |
| Recorte de contexto | `app/services/source_context.py` → `select_source_context()` | Fuente única del contexto que ven writer, crítico y reparación. |
| Contrato de respuesta | `app/schemas/adaptation.py` | `RagFuente`, `QualityEvaluation`, `ResponseMetadata`. |
| UI | `frontend/src/app/features/workspace/sello-confianza.component.ts`, `quality-panel.component.ts`, `sources-drawer.component.ts` | Sello, panel de calidad y lista de fuentes. |
| Pruebas | `backend/tests/test_grounding_verification.py`, `test_source_citations_contract.py`, `test_score_lifecycle.py` | Reglas, contrato de citas y ciclo de vida del score. |

---

## 2. Posición en el grafo

```text
planner → writer → deduplicator → grounding_verifier → critic
                                                        │
                        ┌───────────────────────────────┼──────────────────┐
                        ▼                               ▼                  ▼
                     repair                          refiner           formatter
                        │                               │                  │
                        └──────────────► formatter ◄────┘                  ▼
                                                                          END
```

`_should_refine_or_complete()` decide la rama:

1. **`repair`** — hay elementos sin fuente verificada o con claridad `Baja`/`Low`
   que aún no se repararon y queda presupuesto de revisión.
2. **`refiner`** — faltan elementos para llegar al objetivo y el documento tiene
   capacidad restante.
3. **`formatter`** — calidad aprobada o presupuesto agotado.

Presupuesto: `settings.LANGGRAPH_MAX_REVISIONS` (por defecto `2`).

---

## 3. Verificación léxica (`_stage_verify_grounding`)

### 3.1 Resolución del `chunk_id`

El modelo puede citar identificadores con formatos ligeramente distintos. El
verificador construye un mapa de pasajes con varias claves por fragmento:

- el `id` de nivel superior y el `metadata.chunk_id`;
- el prefijo sin sufijo `_child_N`;
- el identificador sin el sufijo numérico final (`parent_12` → `parent`).

Si el `chunk_id` no resuelve, se intenta un emparejamiento por solapamiento de
palabras (≥ `0.25`) contra los pasajes recuperados por RAG.

### 3.2 Reglas aplicadas, en orden

| # | Regla | Umbral | Efecto |
| :--- | :--- | :--- | :--- |
| 1 | Extracto literal contenido en el fragmento (o viceversa) | — | Marca la cita como soportada y **omite** las reglas 2–4. |
| 2 | Anti-negación: todo token de negación de la afirmación debe existir en el fragmento | — | Si falta alguno → cita rechazada. |
| 3 | Entidades numéricas: todo número de la afirmación debe existir en el fragmento | — | Si falta alguno → cita rechazada. |
| 4 | Solapamiento de palabras del extracto | ≥ `0.45` | Marca la cita como soportada. |
| 5 | Solapamiento de palabras del elemento (sin distractores) | ≥ `0.25` | Último recurso si no hay extracto. |
| 6 | Pureza de idioma del texto de anclaje | — | Si falla, revoca **todas** las citas del elemento y marca `language_impure`. |

Detalles relevantes:

- Las reglas 2 y 3 se aplican sobre `_get_grounding_text(item)` /
  `_get_claim_text(item)`, no sobre el texto completo: en un quiz los
  distractores son **intencionadamente** falsos y no deben exigir respaldo.
- El resultado por cita se escribe en `fuentes[i].verificado` (`bool`).
- El elemento queda `grounded = any(verificado)`.

### 3.3 Contexto que recibe el modelo

`select_source_context()` recorta cada fragmento a
`settings.RAG_CONTEXT_SNIPPET_SIZE` (default `1500` caracteres). Si el fragmento
cabe, se entrega completo; si no, la ventana se centra en un extracto de foco y
se alinea a límites de frase o palabra. Writer, crítico y reparación usan **el
mismo** helper, de modo que auditan el mismo texto que se usó para generar.

---

## 4. Auditoría del crítico (`_stage_critic`)

- Plantilla: `app/prompts/auditor.md`.
- Cascada de proveedores: `settings.CRITIC_CASCADE` (Groq → Gemini →
  OpenRouter), con `get_llm_guard()` para cuotas.
- Contexto (`source_facts`): primero los chunks **citados** por los elementos
  (máximo 10), completados con los pasajes RAG no citados. Así el crítico juzga
  con el mismo contexto que el verificador léxico.
- Entrada por elemento: índice, texto de afirmación
  (`_get_critic_audit_text`, sin distractores) y lista de `chunk_id` citados.
- Salida por elemento (`per_item`): `_gid`, `verificado_revisor`, `claridad`
  (`Alta`/`Media`/`Baja`), `issues`.

Si ningún proveedor del crítico responde, se registra
`critic_provider = "evaluador_heuristico"` y se continúa solo con la verificación
léxica.

---

## 5. Cálculo del score

```python
origen_verificado = verificado_lexico and verificado_revisor
anclaje_fuente_score = round(verified_items / max(1, items_generados), 2)
```

Notas de comportamiento:

- El score **es** el ratio de elementos verificados; no se mezcla con la
  claridad pedagógica.
- Si el crítico produjo `per_item`, se respeta su `verificado_revisor` y se
  añade la nota `"N de M elementos verificados."` a `observaciones`.
- Si no hubo auditoría (sin `per_item`), `verificado_revisor` se asume `True` y
  el score queda determinado solo por la vía léxica.
- La reparación invalida el veredicto del crítico de la versión anterior: el
  elemento reparado se vuelve a verificar y a auditar antes de puntuar.
- Los elementos basura (`_is_garbage_item`) y los marcadores `es_fallback` se
  excluyen antes de calcular el ratio.

### Contrato de respuesta

`evaluacion_calidad` (`QualityEvaluation`):

```json
{
  "anclaje_fuente_score": 0.8,
  "claridad_pedagogica": "Alta",
  "observaciones": "4 de 5 elementos verificados. …",
  "por_item": [
    {
      "index": 0,
      "_gid": "ground_0",
      "verificado_lexico": true,
      "verificado_revisor": true,
      "origen_verificado": true,
      "claridad": "Alta",
      "issues": [],
      "es_fallback": false
    }
  ]
}
```

Cada cita (`RagFuente`) expone `chunk_id`, `extracto`, `seccion`, `breadcrumb`,
`pagina`, `similitud_score` y `verificado`.

---

## 6. Reparación

`_node_repair()` reescribe en un solo lote los elementos candidatos:

1. Re-ejecuta `_stage_verify_grounding()` sobre lo reparado.
2. Vuelve a ejecutar el crítico solo sobre esos elementos y fusiona los
   veredictos nuevos por `_gid`.
3. Descarta cualquier veredicto que pertenezca a la versión anterior del
   elemento.
4. Actualiza el contador de revisiones y vuelve a evaluar la rama condicional.

---

## 7. Configuración relacionada

| Ajuste | Default | Efecto |
| :--- | :--- | :--- |
| `LANGGRAPH_MAX_REVISIONS` | `2` | Ciclos máximos de reparación/refinamiento. |
| `RAG_CONTEXT_SNIPPET_SIZE` | `1500` | Presupuesto de caracteres por fragmento entregado al modelo. |
| `CRITIC_CASCADE` | Groq → Gemini → OpenRouter | Proveedores del auditor. |
| `MAX_TOP_K_CHUNKS` | `5` | Pasajes RAG que alimentan la generación. |

---

## 8. Pruebas

```bash
cd backend
uv run --with pytest --with email-validator --with genanki pytest tests/test_grounding_verification.py tests/test_source_citations_contract.py tests/test_score_lifecycle.py
```

Cubren: resolución de `chunk_id`, extracto literal, anti-negación, entidades
numéricas, solapamiento mínimo, pureza de idioma, invalidez del veredicto tras
reparación y consistencia del score con `per_item`.

---

## 9. Limitaciones conocidas

- Los umbrales (`0.45`, `0.25`) son heurísticos y se calibraron con documentos
  técnicos en español; un corpus muy distinto puede requerir ajuste.
- El extracto literal se acepta sin pasar por las comprobaciones de negación ni
  de cifras: una cita textual siempre se considera válida.
- Si el crítico no está disponible, el score mide solo respaldo léxico.
- Errores presentes en el documento original siguen siendo "anclables": el
  anclaje mide fidelidad a la fuente, no veracidad absoluta.

---

<div align="right">

[Volver al README](../../../../README.md)

</div>
