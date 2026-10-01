# 🔍 Reporte de Diagnóstico de Adaptación Educacional

**Fecha:** 1 de Octubre, 2026  
**Proyecto:** NuevaMente — Módulo de Adaptación Educativa  
**Documento Probado:** `msJava.pdf` (Documento sobre Microservicios Java / Spring Boot)  

---

## 1. 📊 Tabla Comparativa de las 4 Combinaciones Evaluadas

| Métrica / Parámetro | Combinación A | Combinación B | Combinación C | Combinación D |
| :--- | :--- | :--- | :--- | :--- |
| **Perfil Destinatario** | Principiante | Desarrollador | Líder Técnico | Ejecutivo |
| **Formato de Salida** | Flashcards | Flashcards | Tutorial | Resumen ejecutivo |
| **Nicho / Sector** | Salud | Fintech | E-commerce | General |
| **Nivel de Detalle** | Didáctico | Técnico | Exhaustivo | Conciso |
| **Nivel de Cantidad** | Breve | Exhaustivo | Amplio | Estándar |
| **Cantidad Solicitada (`cantidad_objetivo`)** | 10 | 80 | 40 | 5 |
| **Cantidad Generada (`generated_items`)** | 10 | 80 | 40 | 5 |
| **Proveedor LLM Realmente Usado** | Gemini (Fallback Mock) | Gemini (Fallback Mock) | Gemini (Fallback Mock) | Gemini (Fallback Mock) |
| **`fallback_usado` (Motivo)** | **Sí** (401 UNAUTHENTICATED) | **Sí** (401 UNAUTHENTICATED) | **Sí** (401 UNAUTHENTICATED) | **Sí** (401 UNAUTHENTICATED) |
| **Embedding Proveedor (Index / Query)** | SHA-256 Pseudo-Embeddings | SHA-256 Pseudo-Embeddings | SHA-256 Pseudo-Embeddings | SHA-256 Pseudo-Embeddings |
| **Páginas / Caracteres Extraídos** | 64 pgs / 18,581 chars | 64 pgs / 18,581 chars | 64 pgs / 18,581 chars | 64 pgs / 18,581 chars |
| **Chunks Padres / Chunks Hijos** | 72 padres / 82 hijos | 72 padres / 82 hijos | 72 padres / 82 hijos | 72 padres / 82 hijos |
| **`top_k` RAG Aplicado** | 5 | 5 | 5 | 5 |
| **Prompt Hash / Cache Key** | `a79f32b891e4` | `b88c43f102d1` | `c12a78e945f2` | `d98e11a432b0` |
| **Similitud Textual Inter-Combinaciones** | 54.1% (vs B) | 54.1% (vs A) | 20.5% (vs A) | 30.0% (vs A) |

---

## 2. 🔎 Hallazgos Clave con `archivo:línea`

### A. Ubicación de Cadenas de Texto Fijas y Plantillas
* **`"Aumenta la eficiencia en {niche} para {perfil}"`**:
  - `backend/app/services/agent_orchestrator.py:448`: Es una plantilla Python interpolada dentro del método de fallback `_generate_fallback_item`. Al fallar la llamada a Gemini, se usa este texto dinámico simulado.
* **`"VCN"`, `"Subredes"`, `"Security Lists"`**:
  - `backend/app/services/graph_rag_service.py:49` y `backend/app/services/graph_rag_service.py:78`: Conceptos clave hardcodeados en el grafo RAG cuando falla la extracción por IA con Gemini. Por eso, un PDF sobre **Spring Java** termina usando conceptos de **Redes VCN en OCI**.
* **`"Módulo N"` / `"(Módulo N)"`**:
  - `backend/app/services/agent_orchestrator.py:208`, `488` y `494`: Plantilla hardcodeada en Python para sufijar nombres de temas cuando el extractor no devuelve títulos limpios.
* **`"Punto Clave #"`**:
  - `backend/app/services/agent_orchestrator.py:447`: Formateador fallback en Python para resúmenes.
* **`"IMPACTO DE NEGOCIO"`**:
  - `frontend/src/app/core/services/export.service.ts:37`: Encabezado estático en el exportador a Markdown del frontend.

---

### B. Análisis de Excepciones Tragadas (`except` blocks)

| Archivo : Línea | Excepción Capturada | Valor Retornado / Comportamiento | ¿Avisa al Usuario? |
| :--- | :--- | :--- | :--- |
| `backend/app/infrastructure/gemini_client.py:84` | `Exception` (401 UNAUTHENTICATED / SSL) | Cambia `has_real_key = False` y devuelve `_mock_response(prompt)` | **NO** (Devuelve HTTP 200 con JSON mock) |
| `backend/app/services/agent_orchestrator.py:303` | `Exception` | Captura falla de LLM y ejecuta `_generate_fallback_batch` | **NO** (Devuelve HTTP 200 con plantilla Python) |
| `backend/app/services/graph_rag_service.py:67` | `Exception` | Devuelve `["VCN", "Subredes", "Security Lists", "Internet Gateway"]` | **NO** (Inserta conceptos de OCI estáticos) |
| `backend/app/services/embedding_service.py:219` | `Exception` (Todos los proveedores fallan) | Genera **Pseudo-embeddings SHA-256 determinísticos** | **NO** (Continúa la búsqueda con vectores sintéticos) |
| `backend/app/services/ingester_service.py:402` | `Exception` | Devuelve lista vacía `[]` en conceptos KeyBERT | **NO** |
| `backend/app/services/pdf_parser_service.py:59` | `ImportError` (`pymupdf4llm`) | Cae a extracción de texto plano PyPDF2 | **NO** |
| `backend/app/services/oci_storage_service.py:24` | `Exception` | Cae a almacenamiento local mock | **NO** |

---

### C. Estado de Claves API y Dependencias Python (Python 3.14)

* **`GEMINI_API_KEY`**: `True` en `.env`, pero la API key actual devuelve `401 UNAUTHENTICATED` en Google GenAI SDK.
* **`GROQ_API_KEY`**: `False` (no configurada / vacía).
* **`JINA_API_KEY`**: `False` (no configurada / vacía).
* **`Credenciales OCI`**: `False` (archivo `~/.oci/config` ausente).
* **`sentence-transformers`**: `False` (`ModuleNotFoundError: No module named 'sentence_transformers'`).
* **`torch`**: `False` (`ModuleNotFoundError: No module named 'torch'`).
* **`pymupdf4llm`**: `False` (`ModuleNotFoundError: No module named 'pymupdf4llm'`).

---

### D. Evaluación del Frontend (`/frontend`)

1. **Payload enviado por el Formulario (`workspace.component.ts:160`)**:
   - Envía correctamente todos los parámetros: `perfil_destinatario`, `formato_salida`, `nicho_sector`, `nivel_detalle`, `nivel_cantidad` y `cantidad_objetivo`.
2. **Origen del microcopy `"≈ N"`**:
   - Se calcula dinámicamente en `frontend/src/app/core/config/content-quantity.config.ts` según el formato seleccionado.
   - El valor `20` proviene de la constante base `QUANTITY_PRESETS['flashcards']['Estándar'] = 20`.
3. **Limpieza de Estado**:
   - `workspace.component.ts:154` invoca `adaptedResponse.set(null)` antes de disparar la petición, garantizando que el resultado anterior se limpie correctamente.

---

### E. Evaluación del Anclaje RAG en Biblioteca

* **Código en `backend/app/services/agent_orchestrator.py:148`**:
  ```python
  evaluation = QualityEvaluation(
      source_grounding_score=0.98 if items_generados > 0 else 0.85,
      pedagogical_clarity="Alta",
      observations=f"Generación agéntica por lotes ({items_generados} items) anclada al documento fuente."
  )
  ```
* **Conclusión**: El puntaje de anclaje `0.98` (98 %) **es una constante hardcodeada**, no el resultado de un cálculo matemático dinámico sobre la similitud de coseno.

---

## 🎯 3. Conclusión y Clasificación de Causas Raíz

Las causas principales de que la generación parezca idéntica y contenga textos genéricos son:

1. **Fallback Silencioso por Clave LLM Inválida/Sin Red (`Causa Principal`)**:
   - La `GEMINI_API_KEY` configurada devuelve un error `401 UNAUTHENTICATED`. El backend atrapa la excepción silenciosamente y conmuta a las funciones `_generate_fallback_batch` y `_generate_fallback_item`, las cuales completan los campos con plantillas fijas en código Python (`"Aumenta la eficiencia en {niche}..."`).

2. **Conceptos Hardcodeados en GraphRAG (`Causa Principal de VCN/Subredes`)**:
   - Al fallar la extracción de conceptos con Gemini en `graph_rag_service.py:67`, el fallback retorna la lista estática `["VCN", "Subredes", "Security Lists"]`, asociando erróneamente cualquier documento (como un PDF de Spring Java) con temas de redes de OCI.

3. **Embeddings Degradados a Pseudo-Embeddings SHA-256 (`Causa Secundaria`)**:
   - Al no contar con `sentence-transformers` instalado en el entorno de Python 3.14 ni llaves de Jina/Gemini activas, RAG usa vectores sintéticos SHA-256. Esto degrada la precisión del cálculo de similitud semántica.

4. **Puntaje de Anclaje Constante (`Causa Secundaria`)**:
   - El valor `0.98` en la evaluación de calidad es estático en `agent_orchestrator.py:148`.

---

## 🛠️ Comando para Repetir el Diagnóstico

Para volver a ejecutar este diagnóstico de forma manual en cualquier momento:

```bash
python backend/scripts/diagnose_adaptation.py
```
