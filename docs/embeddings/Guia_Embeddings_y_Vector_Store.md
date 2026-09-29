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
1. Verificación previa de cuota (antes de enviar nada)
   - Se simula el envío de todos los lotes contra el limitador compartido de Gemini.
   - Cuota diaria (GEMINI_SAFE_RPD) insuficiente para el documento: se omite Gemini.
   - Espera total estimada mayor a GEMINI_MAX_WAIT_SECONDS: se omite Gemini.
   - Tokens estimados > JINA_SAFE_TPM (90K): se omite Jina.
   - El modelo local siempre es candidato (sin cuotas).
   - Omitir un proveedor en esta etapa no gasta ninguna request.
               │
               ▼
2. Vectorización por lotes con control de cuota y fallback en cascada
   - Gemini: lotes de hasta 20 textos; el limitador espera lo necesario entre lotes.
   - Jina: lotes de hasta 50 textos.
   - Falla antes del primer vector: cambio inmediato al siguiente proveedor.
   - Falla a mitad del documento: espera y retoma el lote fallido con el mismo proveedor;
     si se agotan los reintentos, descarta lo generado y re-embebe todo con el siguiente.
   - Si todos los proveedores fallan: pausa y reintenta la cadena completa (máx. 2 rondas).
   - Atómico por documento: nunca se mezclan vectores de distintos proveedores en un índice.
   - Dimensión fija unificada: 768 dimensiones para todos los proveedores.
               │
               ▼
3. Control Estricto de Compatibilidad (Model Tracking)
   - Se registra en los metadatos qué modelo generó el índice (ej. models/gemini-embedding-001@768).
   - En la consulta (retrieval), se resuelve el vector de búsqueda con el mismo modelo del documento.
```

### Conceptos Clave
- **Dimensión fija entre proveedores:** `EMBEDDING_DIMENSIONS` (por defecto **768**) se aplica a los tres proveedores: Gemini vía `output_dimensionality`, Jina vía el parámetro `dimensions`, y el modelo local eligiendo uno que produce 768 (`mpnet`). Esto permite que un índice FAISS local sea directamente compatible con una futura tabla `pgvector`, sin reindexar.
- **Espacio vectorial e integridad atómica:** Aunque la dimensión coincida, cada modelo proyecta el texto en un mapa matemático distinto. Por eso, todos los vectores de un documento deben venir del mismo proveedor. Si un proveedor no puede terminar el documento, se descartan los vectores parciales y se procesa el documento completo con el siguiente. El `model_name` resultante se actualiza en el `VectorStore` para que la búsqueda por similitud no compare espacios incompatibles.
- **La cuota de Gemini se cuenta por texto, no por llamada:** cada texto de un lote cuenta como una request para el límite por minuto (RPM) y el diario (RPD). Enviar lotes de 20 reduce las llamadas HTTP, pero **no** reduce la cuota consumida: 20 textos siguen siendo 20 requests. Por eso el control se hace por texto.
- **Limitador de cuota compartido (`embedding_rate_limiter.py`):** lleva una ventana deslizante de 60 s (requests y tokens) y una ventana diaria móvil de 24 h. Es un único limitador por proceso, compartido por todas las instancias de `EmbeddingService` y por las consultas. Usa márgenes bajo los límites reales (`GEMINI_SAFE_RPM=80` frente a 100, `GEMINI_SAFE_RPD=900` frente a 1000). Limitaciones conocidas: vive en memoria (se reinicia con el proceso), no ve el consumo de otros procesos o herramientas que usen la misma API key, y la ventana diaria es una aproximación móvil del reinicio real del proveedor. Un 429 real de Gemini sigue siendo el respaldo.
- **Reglas de fallo al indexar un documento:**

| Situación | Comportamiento |
|---|---|
| Gemini no tiene cuota diaria suficiente, o la espera estimada supera el máximo | Se omite antes de enviar; pasa al siguiente proveedor sin gastar requests |
| Falla el primer lote (aún no hay vectores) | Cambio inmediato al siguiente proveedor |
| Falla un lote posterior | Espera (el `retryDelay` del error, o 60 s) y reintenta ese lote, hasta `EMBEDDING_PARTIAL_RETRIES` veces |
| Se agotan esos reintentos, o la cuota diaria se acaba a mitad | Descarta lo generado y re-embebe el documento completo con el siguiente proveedor |
| Fallan todos los proveedores | Pausa de `EMBEDDING_RETRY_WAIT_SECONDS` y reintenta la cadena, hasta `EMBEDDING_CHAIN_ROUNDS` rondas; luego lanza error (el pipeline marca el documento `failed`) |

- **División de lotes rechazados:** si un proveedor rechaza un lote por su tamaño, el lote se divide a la mitad y se reintenta cada mitad. En Gemini solo ocurre ante un error 400; en Jina, ante cualquier error que no sea de cuota (429).
- **Consultas (`is_query=True`):** las consultas sin modelo objetivo nunca esperan; pasan al siguiente proveedor si Gemini no tiene cupo. Las consultas con `model_name` (las de retrieval) sí esperan cupo, porque su vector debe venir del mismo modelo que construyó el índice.
- **Modelo local:** se carga una sola vez por proceso y es compartido por todas las instancias. Si la carga falla (por ejemplo, por una dependencia faltante de `transformers`), se registra la causa real con su traceback, se recuerda el fallo para no reintentar el import en cada llamada, y el error final incluye el motivo. `max_seq_length` se fija en `LOCAL_MAX_SEQ_LENGTH` (256 por defecto, máximo 512) y se avisa en el log cuando algún texto lo supera y será truncado.
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
# Internamente se envía en lotes: hasta GEMINI_BATCH_SIZE textos por llamada en
# Gemini (esperando cupo en el limitador compartido) y JINA_BATCH_SIZE en Jina.
# Todos los textos de la lista se vectorizan con un único proveedor.
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

### Reportar el Progreso (`on_progress`)
`embed_batch` y `process_and_index_document` aceptan un callback opcional que recibe un diccionario por evento. Sin callback, todo funciona igual.

```python
def mostrar(evento: dict) -> None:
    print(evento["stage"], "|", evento["message"])

embedding_svc.embed_batch(textos, on_progress=mostrar)

# Pipeline completo (agrega las etapas de subida, ingesta e indexado)
record = process_and_index_document(local_path="doc.pdf", on_progress=mostrar)
```

Claves del evento: `stage` y `message` (texto en español listo para mostrar), y opcionalmente `current`, `total`, `wait_seconds` y `provider`.

| `stage` | Quién lo emite | Cuándo |
|---|---|---|
| `uploading`, `ingesting`, `indexing`, `ready`, `failed` | Pipeline | Etapas del procesamiento del documento |
| `embedding` | Servicio de embeddings | Tras cada lote (`current` / `total` textos) |
| `waiting` | Servicio de embeddings | Esperando cupo de Gemini, o pausa entre rondas de la cadena (`wait_seconds`) |
| `retrying` | Servicio de embeddings | Reintento tras un fallo a mitad del documento |
| `switching_provider` | Servicio de embeddings | Cambio de proveedor |

El callback se ejecuta en el hilo que llama, y si lanza un error se ignora. Como el pipeline puede bloquearse hasta 60 s en una espera, una UI debe ejecutarlo en un hilo aparte (la UI de prueba usa un hilo y una cola).

### Verificar el Modelo Local
```python
disponible, mensaje = EmbeddingService().check_local_available()
print(disponible, mensaje)   # (False, "Missing dependency 'x' required by ...") si falta algo
```
No lanza excepciones. Comprueba que el modelo cargue y que su dimensión coincida con `EMBEDDING_DIMENSIONS`. Conviene llamarlo al arrancar la aplicación, para ver un problema de dependencias en ese momento y no a mitad de un fallback. Ojo: la primera vez descarga el modelo, lo que puede tardar.

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

# Límites de Gemini (cada texto cuenta como una request)
GEMINI_MAX_RPM = 100                # límites publicados por el proveedor (referencia)
GEMINI_MAX_TPM = 30000
GEMINI_MAX_RPD = 1000
GEMINI_SAFE_RPM = 80                # techo que aplica el limitador (con margen)
GEMINI_SAFE_TPM = 25000
GEMINI_SAFE_RPD = 900
GEMINI_BATCH_SIZE = 20              # máximo de textos por llamada (tope efectivo: GEMINI_SAFE_RPM)
GEMINI_MAX_WAIT_SECONDS = 600       # espera total aceptada para un documento antes de omitir Gemini

JINA_MAX_RPM = 100
JINA_MAX_TPM = 100000
JINA_SAFE_TPM = 90000               # sobre este volumen estimado se omite Jina
JINA_BATCH_SIZE = 50

LOCAL_BATCH_SIZE = 32
LOCAL_MAX_SEQ_LENGTH = 256          # tokens por texto en el modelo local (máx. 512)
EMBEDDING_FALLBACK_CHAIN = ["gemini", "jina", "local"]

# Reintentos y esperas al indexar un documento
EMBEDDING_CHAIN_ROUNDS = 2          # pasadas completas por la cadena de proveedores
EMBEDDING_PARTIAL_RETRIES = 2       # esperas permitidas tras un fallo a mitad del documento
EMBEDDING_RETRY_WAIT_SECONDS = 60   # espera por defecto si el proveedor no indica una

VECTOR_STORE_METHOD = "faiss"       # 'faiss' (por documento) o 'pgvector' (rama Supabase)
VECTOR_STORE_DIR = "vector_store"

USE_KEYBERT_CONCEPTS = False        # extracción de conceptos clave en ingesta (ver doc de Ingestión)
```

Si una API key gratuita se satura seguido, baja `GEMINI_SAFE_RPM` / `GEMINI_SAFE_RPD` o `GEMINI_BATCH_SIZE`; si otras herramientas usan la misma key, deja más margen.

---

## 4. Pruebas Manuales con `uv`

Para validar los módulos de forma aislada:

### Test de Embeddings
```powershell
cd backend
uv run python tests/manual/test_embedding.py
```
1. Generación de vector individual, de consulta y batch vía Google Gemini (prueba 1) y Jina AI (prueba 2), verificando que ambos entreguen 768 dimensiones. Son pruebas en vivo y consumen cuota real.
2. Verificación del `model_name` con el sufijo de dimensión y rechazo de compatibilidad cruzada entre modelos (prueba 3).
3. División de un lote de Jina rechazado por tamaño, con mock (prueba 4).
4. Cambio inmediato de Gemini a Jina cuando Gemini falla en el primer lote, sin reintentos (prueba 5).
5. Cascada completa hasta el modelo local cuando Gemini y Jina fallan (prueba 6).
6. Ruteo proactivo: Gemini se omite, sin gastar cuota, cuando la cuota diaria no alcanza para el documento (prueba 7).

Las pruebas con mocks llaman a `reset_gemini_limiter()` al inicio, porque el limitador es global del proceso y arrastraría la cuota de pruebas anteriores.

**Pendiente de agregar:** pruebas propias del limitador (`embedding_rate_limiter.py`: ventana deslizante, cuota diaria, `estimate_wait`), del reintento tras un fallo a mitad del documento, del comportamiento de las consultas y del modelo local. Por ahora se validan desde la UI de prueba.

### Prueba de Extremo a Extremo desde la UI
La UI de prueba (`upload_test_ui.py`, en `frontend_temp`) ejecuta el pipeline completo con un documento real y muestra el progreso en vivo: lote actual, esperas de cuota, reintentos y cambios de proveedor. Al terminar muestra el proveedor y modelo usados y muestras de chunks y vectores. Al iniciar imprime en consola `[Fallback local] OK / NO DISPONIBLE` con el motivo, para detectar de entrada si el modelo local puede cargar.

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