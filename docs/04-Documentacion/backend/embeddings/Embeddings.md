# Módulo de Embeddings

> `docs/04-Documentacion/backend/embeddings/` · [Volver al README](../../../../README.md)

Este documento describe cómo NuevaMente convierte texto en vectores
(*embeddings*) y cómo controla cuotas y fallbacks. El almacenamiento de esos
vectores (FAISS) se documenta en [Almacén Vectorial](Almacen_Vectorial.md).

---

## 1. Explicación simple: ¿cómo funciona?

La ingesta divide un documento en fragmentos de texto, pero comparar
significado no se puede hacer con palabras exactas. Para eso se generan
**embeddings**: vectores numéricos de alta dimensionalidad que permiten medir
similitud semántica.

```text
[ Textos de chunks / consulta ]
               │
               ▼
1. Verificación previa de cuota (sin gastar requests)
   - Cuota diaria de Gemini insuficiente → se omite Gemini.
   - Espera estimada > GEMINI_MAX_WAIT_SECONDS → se omite Gemini.
   - Tokens estimados > JINA_SAFE_TPM → se omite Jina.
   - El modelo local siempre es candidato (sin cuotas).
               │
               ▼
2. Vectorización por lotes con fallback en cascada
   - Gemini (lotes de 20) → Jina (lotes de 50) → Local.
   - Atómico por documento: nunca se mezclan vectores de proveedores distintos.
   - Dimensión fija unificada: 768 para todos los proveedores.
               │
               ▼
3. Registro del modelo (Model Tracking)
   - Se guarda en el índice qué modelo lo generó (ej. models/gemini-embedding-001@768).
   - En la consulta se usa el mismo modelo del documento.
```

### Conceptos clave

- **Cascada de proveedores:** Gemini → Jina → Local. Si un proveedor falla antes
  del primer vector, se cambia de inmediato; si falla a mitad del documento, se
  reintenta el lote y, de agotarse, se descarta lo parcial y se re-embebe todo
  con el siguiente proveedor.
- **Dimensión fija (768):** `EMBEDDING_DIMENSIONS` se aplica a los tres
  proveedores, de modo que un índice FAISS local sea compatible con una futura
  tabla `pgvector` sin reindexar.
- **Espacio vectorial e integridad atómica:** aunque coincida la dimensión, cada
  modelo proyecta en un mapa distinto; por eso todos los vectores de un
  documento deben venir del mismo proveedor.
- **La cuota de Gemini se cuenta por texto, no por llamada:** 20 textos siguen
  siendo 20 requests; por eso el control es por texto.
- **`model_id` vs. `model_name`:** `model_id` es el identificador enviado a la
  API (`models/gemini-embedding-001`); `model_name` es la etiqueta guardada en el
  índice (`models/gemini-embedding-001@768`), con la dimensión incluida.
- **Task Type:** distingue vectorizar un documento (`RETRIEVAL_DOCUMENT`) de
  vectorizar una consulta (`RETRIEVAL_QUERY`), controlado por `is_query`.

---

## 2. Guía rápida para desarrolladores

```python
from app.services.embedding_service import EmbeddingService

# 1. Inicialización según entorno (por defecto: API Gemini)
embedding_svc = EmbeddingService()

print(embedding_svc.method)      # 'api' o 'local'
print(embedding_svc.provider)    # 'gemini' o 'jina'
print(embedding_svc.model_id)    # 'models/gemini-embedding-001'
print(embedding_svc.model_name)  # 'models/gemini-embedding-001@768'
print(embedding_svc.dimensions)  # 768

# 2. Vectorizar un documento y una consulta
vector_doc = embedding_svc.embed_text("Una VCN es una red virtual privada.", is_query=False)
vector_query = embedding_svc.embed_text("¿Qué es una VCN?", is_query=True)

# 3. Vectorización por lote
vectores_batch = embedding_svc.embed_batch(["texto uno", "texto dos"])
```

También se puede forzar un proveedor o método:

```python
jina_svc = EmbeddingService(method="api", provider="jina")
local_svc = EmbeddingService(method="local")   # sentence-transformers, sin conexión
```

### Reportar progreso (`on_progress`)

`embed_batch` recibe un callback opcional que reporta etapas del proceso. Las
más relevantes: `embedding` (tras cada lote), `waiting` (espera de cuota),
`retrying` y `switching_provider`. El callback se ejecuta en el hilo que llama;
si lanza un error, se ignora.

### Verificar el modelo local

```python
disponible, mensaje = EmbeddingService().check_local_available()
print(disponible, mensaje)
```

No lanza excepciones; conviene llamarlo al arrancar la aplicación. La primera
vez descarga el modelo, lo que puede tardar.

---

## 3. Configuración del entorno

Las API keys van en `backend/.env` (nunca se versionan). El resto tiene defaults
razonables en `app/core/config.py`:

```dotenv
# backend/.env
GEMINI_API_KEY=AIzaSy...
JINA_API_KEY=jina_...
```

```python
# Defaults en app/core/config.py (no requieren estar en .env)
EMBEDDING_METHOD = "api"            # 'api' o 'local'
EMBEDDING_API_PROVIDER = "gemini"   # 'gemini' o 'jina'
EMBEDDING_DIMENSIONS = 768          # fija en los tres proveedores

GEMINI_SAFE_RPM = 80                # techo aplicado por el limitador (con margen)
GEMINI_SAFE_TPM = 25000
GEMINI_SAFE_RPD = 900
GEMINI_BATCH_SIZE = 20
GEMINI_MAX_WAIT_SECONDS = 600

JINA_SAFE_TPM = 90000
JINA_BATCH_SIZE = 50

LOCAL_MAX_SEQ_LENGTH = 256
EMBEDDING_FALLBACK_CHAIN = ["gemini", "jina", "local"]

EMBEDDING_CHAIN_ROUNDS = 2          # pasadas completas por la cadena
EMBEDDING_PARTIAL_RETRIES = 2       # esperas tras un fallo a mitad del documento
EMBEDDING_RETRY_WAIT_SECONDS = 60
```

> `EMBEDDING_BATCH_SIZE` existe en `config.py` pero no lo usa ningún servicio: el
> tamaño de lote real lo fijan `GEMINI_BATCH_SIZE` y `JINA_BATCH_SIZE`. No lo
> configures esperando un efecto.

Si una API key gratuita se satura seguido, baja `GEMINI_SAFE_RPM` /
`GEMINI_SAFE_RPD` o `GEMINI_BATCH_SIZE`.

---

## 4. Pruebas manuales

```powershell
cd backend
uv run python tests/manual/verify_fixes.py
```

El script comprueba, entre otras cosas, la generación de embeddings y el
`model_name` con sufijo de dimensión. Para las pruebas de la suite:

```powershell
uv run --with pytest --with email-validator --with genanki pytest tests/test_embedding_service.py
```

**Pendiente:** pruebas propias del limitador (`embedding_rate_limiter.py`) y del
reintento tras un fallo a mitad del documento.

---

<div align="right">

[Volver al README](../../../../README.md)

</div>

