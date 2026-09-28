# Módulo de Embeddings y Vector Store — NuevaMente

Este documento describe la arquitectura, funcionamiento e instrucciones de uso del módulo de generación de embeddings vectoriales y su compatibilidad con el pipeline de recuperación RAG en NuevaMente.

---

## 1. Explicación Simple: ¿Cómo Funciona?

Cuando el módulo de ingestión divide un documento en pequeños fragmentos (chunks), estos siguen siendo texto plano. Las computadoras no pueden comparar fácilmente el significado profundo de dos oraciones basándose únicamente en palabras exactas.

Para resolver esto, convertimos el texto en **Embeddings** (vectores numéricos de alta dimensionalidad):

```
[ Texto de Chunks / Consulta ]
               │
               ▼
1. Estimación de Tokens y Ruteo Proactivo (Etapa Previa)
   - Analiza el volumen real de chunks e hijos generados tras la partición.
   - Si tokens estimados <= 25K TPM: procesa con Google Gemini (100 PTM / 30K TPM).
   - Si 25K < tokens <= 90K TPM: conmuta proactivamente a Jina AI (100 PTM / 100K TPM).
   - Si tokens > 90K TPM: conmuta proactivamente al modelo Local (sin límites de cuota).
               │
               ▼
2. Vectorización por Lotes y Fallback en Cascada Atómico
   - Gemini: lotes nativos de 20 chunks (contents=[...]), reduciendo peticiones PTM en un 95%.
   - Jina: lotes de 50 chunks con reducción recursiva en caso de rechazo.
   - Cascada reactiva ante errores (429 / Cuota / Red): Gemini -> Jina -> Local.
   - Atómico por documento: nunca se mezclan vectores de distintos proveedores en un mismo índice.
   - Dimensión fija unificada: 768 dimensiones para todos los proveedores.
               │
               ▼
3. Control Estricto de Compatibilidad (Model Tracking)
   - Se registra en los metadatos qué modelo generó el índice (ej. models/gemini-embedding-001@768).
   - En la consulta (retrieval), se resuelve el vector de búsqueda con el mismo modelo del documento.
```

### Conceptos Clave
- **Dimensión fija entre proveedores:** `EMBEDDING_DIMENSIONS` (por defecto **768**) se aplica a los tres proveedores: Gemini vía `output_dimensionality`, Jina vía el parámetro `dimensions`, y el modelo local eligiendo uno que produce 768 (`mpnet`). Esto permite que un índice FAISS local sea directamente compatible con una futura tabla `pgvector`, sin reindexar.
- **Espacio Vectorial e Integridad Atómica:** Aunque la dimensión coincida, cada modelo proyecta el texto en un mapa matemático distinto. Por eso, el fallback entre proveedores es **atómico por documento**: si Gemini falla con 429 a mitad de un archivo, se descartan los vectores parciales y se procesa todo el documento con Jina (o Local). El `model_name` resultante se actualiza en el `VectorStore` para que la búsqueda por similitud no compare espacios incompatibles.
- **Ruteo Proactivo según Cuotas (PTM y TPM):** Antes de enviar peticiones a la API, el servicio estima los tokens reales de los fragmentos hijos (`estimate_tokens`). Si un documento requeriría demoras artificiales en Gemini por sobrepasar los 25K–30K TPM, el sistema conmuta de forma preventiva a Jina (100K TPM), acelerando el procesamiento.
- **Batching Nativo en Gemini y Jina:** En lugar de realizar una llamada HTTP por cada fragmento (lo que agotaría de inmediato el límite de 100 PTM), Gemini envía lotes de 20 chunks por llamada (`GEMINI_BATCH_SIZE = 20`) y Jina lotes de 50 (`JINA_BATCH_SIZE = 50`), reduciendo drásticamente las solicitudes de red.
- **`model_id` vs. `model_name`:** `model_id` es el identificador real enviado a la API (ej. `models/gemini-embedding-001`). `model_name` es la etiqueta guardada en el almacén vectorial (`models/gemini-embedding-001@768`), que incluye la dimensión para asegurar compatibilidad.
- **Task Type:** Distingue entre vectorizar un documento (`RETRIEVAL_DOCUMENT` en Gemini, `retrieval.passage` en Jina) y vectorizar una consulta del usuario (`RETRIEVAL_QUERY` / `retrieval.query`). Se controla con el parámetro `is_query`.

---

## 2. Guía Rápida para Desarrolladores: ¿Cómo Usarlo?

Esta sección explica cómo inicializar y usar el servicio de embeddings en el código.

### Uso Directo en Python

```python
from app.services.embedding_service import EmbeddingService

# 1. Inicialización según variables de entorno (por defecto: API Gemini)
embedding_svc = EmbeddingService()

print(f"Método activo: {embedding_svc.method}")       # 'api' o 'local'
print(f"Proveedor: {embedding_svc.provider}")         # 'gemini' o 'jina'
print(f"Model ID (API): {embedding_svc.model_id}")    # 'models/gemini-embedding-001'
print(f"Model tag (store): {embedding_svc.model_name}")  # 'models/gemini-embedding-001@768'
print(f"Dimensión: {embedding_svc.dimensions}")       # 768

# 2. Vectorizar un documento
doc_text = "Una Virtual Cloud Network (VCN) es una red virtual privada en OCI."
vector_doc = embedding_svc.embed_text(doc_text, is_query=False)
print(f"Dimensión del vector: {len(vector_doc)}")  # 768

# 3. Vectorizar una consulta de búsqueda
query_text = "¿Qué es una VCN?"
vector_query = embedding_svc.embed_text(query_text, is_query=True)

# 4. Vectorización por lote (Batch)
# Internamente se envía en grupos de EMBEDDING_BATCH_SIZE (Jina), o de a uno
# con reintentos (Gemini, que no expone un endpoint de batch público).
textos = [
    "Las subredes dividen la red en segmentos públicos y privados.",
    "Las listas de seguridad funcionan como firewalls virtuales."
]
vectores_batch = embedding_svc.embed_batch(textos)
print(f"Vectores generados: {len(vectores_batch)}")
```

### Inicialización con Proveedor Específico
Puedes forzar un proveedor o método al instanciar el servicio:

```python
# Usar Jina AI
jina_svc = EmbeddingService(method="api", provider="jina")

# Usar modelo local (sentence-transformers, sin conexión)
local_svc = EmbeddingService(method="local")
```

> **Nota:** si cambias `EMBEDDING_DIMENSIONS` en `.env`, el modelo local (`mpnet`) tiene una salida fija de 768. Un valor distinto en esa variable hará que `embed_batch` lance un error explícito al no coincidir la dimensión — es intencional, para no indexar vectores truncados en silencio.

### Uso del Vector Store (FAISS)

Hay dos formas de usar el vector store: la **fábrica por documento** (recomendada, usada por el resto del pipeline) y el uso directo de `FAISSVectorStore` (para pruebas puntuales o scripts).

#### Fábrica por documento (recomendado)

```python
from app.services.vector_store_service import get_store, save_store

document_id = "un-uuid-de-documento"

# 1. Abre el índice del documento si existe, o crea uno vacío con la
#    dimensión configurada (EMBEDDING_DIMENSIONS).
vector_store = get_store(document_id)

# 2. Indexar child chunks con sus vectores y registrar padres
vector_store.add_documents(
    child_chunks=rag_payload["child_chunks"],
    embeddings=vectores_batch,
    parent_chunks=rag_payload["parent_chunks"],
    model_name=embedding_svc.model_name,
)

# 3. Persistir en vector_store/{document_id}/ y refrescar el caché en memoria
save_store(document_id, vector_store)
```

Cada documento tiene su propio índice (`vector_store/{document_id}/`), porque la generación de contenido siempre trabaja sobre un único documento — nunca se busca entre varios a la vez.

> `rag_payload["child_chunks"]` y `rag_payload["parent_chunks"]` ya llegan validados: `IngesterService.build_rag_chunks()` los construye contra los modelos `ChildChunk` / `ParentChunk` de `app/schemas/rag_chunks.py` antes de convertirlos a diccionario. Ese archivo es la fuente de verdad de qué claves esperar en cada dict — ver el documento de Ingestión para más detalle.

#### Uso directo de `FAISSVectorStore` (bajo nivel)

```python
from app.services.vector_store_service import FAISSVectorStore

# 1. Crear el índice FAISS para el modelo activo
vector_store = FAISSVectorStore(model_name=embedding_svc.model_name)

# 2. Indexar child chunks con sus vectores y registrar padres
vector_store.add_documents(
    child_chunks=rag_payload["child_chunks"],
    embeddings=vectores_batch,
    parent_chunks=rag_payload["parent_chunks"],
    model_name=embedding_svc.model_name,
)

# 3. Búsqueda semántica de fragmentos hijos
hijos_top = vector_store.similarity_search(
    query_embedding=vector_query,
    query_model_name=embedding_svc.model_name,
    top_k=3,
)

# 4. Recuperación directa de Parent Chunks completos para el LLM
padres_top = vector_store.retrieve_parent_chunks(
    query_embedding=vector_query,
    query_model_name=embedding_svc.model_name,
    top_k_parents=2,
)

# 5. Persistencia en disco
vector_store.save("vector_store/mi_indice")

# 6. Carga desde disco
store_cargado = FAISSVectorStore()
store_cargado.load("vector_store/mi_indice")
```

> Para búsquedas dentro del pipeline de RAG (no pruebas sueltas), usa `retrieval_service.py`, que ya combina esta búsqueda densa con BM25 y un reranker — ver el documento de ese módulo.

---

## 3. Configuración del Entorno

Las API keys van en `backend/.env` (nunca se versionan). El resto de valores ya tiene un default razonable en `app/core/config.py` y solo hace falta declararlos en `.env` si quieres sobrescribirlos:

```dotenv
# API Keys (backend/.env)
GEMINI_API_KEY=AIzaSy...
JINA_API_KEY=jina_...
```

```python
# Defaults en app/core/config.py (no requieren estar en .env)
EMBEDDING_METHOD = "api"            # 'api' o 'local'
EMBEDDING_API_PROVIDER = "gemini"   # 'gemini' o 'jina'
EMBEDDING_DIMENSIONS = 768          # fija en los tres proveedores
EMBEDDING_BATCH_SIZE = 50           # tamaño de lote inicial

# Límites de cuotas y lotes por proveedor
GEMINI_MAX_RPM = 100
GEMINI_MAX_TPM = 30000
GEMINI_SAFE_TPM = 25000             # Umbral seguro antes de conmutar a Jina
GEMINI_BATCH_SIZE = 20              # Chunks agrupados por llamada a Gemini

JINA_MAX_RPM = 100
JINA_MAX_TPM = 100000
JINA_SAFE_TPM = 90000               # Umbral seguro antes de conmutar a Local
JINA_BATCH_SIZE = 50

LOCAL_BATCH_SIZE = 32
EMBEDDING_FALLBACK_CHAIN = ["gemini", "jina", "local"]

VECTOR_STORE_METHOD = "faiss"       # 'faiss' (por documento) o 'pgvector' (rama Supabase)
VECTOR_STORE_DIR = "vector_store"

USE_KEYBERT_CONCEPTS = False        # extracción de conceptos clave en ingesta (ver doc de Ingestión)
```

---

## 4. Pruebas Manuales con `uv`

Para validar los módulos de forma aislada:

### Test de Embeddings
```powershell
cd backend
uv run python tests/manual/test_embedding.py
```
1. Generación de vector individual, de consulta y batch vía Google Gemini y Jina AI, verificando que ambos entreguen 768 dimensiones.
2. Verificación de rechazo de compatibilidad cruzada entre modelos de distinto `model_name`.
3. **Pendiente de agregar:** una prueba que fuerce un fallo simulado en un lote de Jina y confirme que el tamaño de lote se reduce a la mitad en vez de cambiar de proveedor.

### Test Completo de Cadena con FAISS Vector Store
```powershell
cd backend
uv run python tests/manual/test_vector_store.py
```
Ejecuta la cadena de extremo a extremo:
1. Ingesta y chunking jerárquico Padre-Hijo.
2. Generación de embeddings reales (768 dimensiones).
3. Indexación en FAISS y cálculo de similitud coseno.
4. Búsqueda semántica y resolución automática de Parent Chunks.
5. Persistencia y recarga desde disco (`index.faiss` + `metadata.json`).
6. Bloqueo estricto por intento de búsqueda con modelo incompatible.
7. **Pendiente de agregar:** una prueba de `get_store()` / `save_store()` que confirme que abrir el mismo `document_id` dos veces reutiliza el índice del caché en memoria.