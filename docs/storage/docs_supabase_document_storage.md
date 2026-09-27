# Almacenamiento de Documentos con Supabase — NuevaMente

Este documento cubre dos cosas: **la configuración manual que hay que hacer una vez** en el dashboard de Supabase, y **cómo usar en código** `document_storage_service.py` (el archivo original) y `document_repository.py` (su metadata: título, estado, `object_key`).

Es la rama de "con login" del proyecto — usa el mismo proyecto de Supabase que se usará más adelante para Auth y `pgvector`, aunque hoy no haya login todavía (`user_id` queda en `null`).

---

## 1. Configuración manual (una sola vez, en el dashboard de Supabase)

### 1.1 Crear el bucket de Storage
1. Entra a tu proyecto en [supabase.com](https://supabase.com) → **Storage** → **New bucket**.
2. Nombre exacto: `document-source` (debe coincidir con `SUPABASE_BUCKET_DOCUMENTS` en `config.py`).
3. Márcalo como **privado** (no "Public bucket"). El backend accede con la key `service_role`, que se salta cualquier política — no hace falta exponerlo públicamente.

### 1.2 Crear la tabla `documents`
1. Ve a **SQL Editor** → **New query**.
2. Pega y ejecuta el contenido de `migrations/001_documents.sql` (incluido en este mismo commit).
3. Verifica en **Table Editor** que la tabla `documents` aparece con sus columnas.

> Row Level Security (RLS) no se activa todavía a propósito: el backend usa `service_role`, que ignora RLS de cualquier forma. Cuando exista login y el frontend necesite consultar Supabase directamente (no a través del backend), ahí sí habrá que activar RLS con una policy `user_id = auth.uid()`. Por ahora, activar RLS sin políticas solo bloquearía sin necesidad.

### 1.3 Obtener las credenciales
1. **Project Settings** → **API**.
2. Copia **Project URL** → va en `SUPABASE_URL`.
3. Copia la key de la fila **`service_role`** (⚠️ no la de `anon`/`public`) → va en `SUPABASE_KEY`.

### 1.4 Variables de entorno

```bash
# backend/.env — nunca se sube a git
SUPABASE_URL=https://tuproyecto.supabase.co
SUPABASE_KEY=eyJh...   # service_role
```

```bash
# backend/.env.example — sí se sube, con placeholder
SUPABASE_URL=your_supabase_project_url_here
SUPABASE_KEY=your_supabase_service_role_key_here
```

### 1.5 Instalar la dependencia
```bash
cd backend
uv add supabase
```

---

## 2. Guía Rápida para Desarrolladores: ¿Cómo Usarlo?

### Subir y descargar el archivo original

```python
from app.services.document_storage_service import get_document_storage

storage = get_document_storage()  # SupabaseStorageService, según STORAGE_METHOD

# Subir (típicamente sobre un archivo temporal recién recibido por el endpoint)
object_key = storage.upload_document(
    local_path="/tmp/manual_oci.pdf",
    user_id=None,          # None hasta que exista login
    document_id="un-uuid-de-documento",
)
print(object_key)  # ej: "anonymous/un-uuid-de-documento.pdf"

# Descargar (por ejemplo, para reprocesar un documento ya subido)
local_path = storage.download_document(
    object_key=object_key,
    destination_path="/tmp/reprocesar/manual_oci.pdf",
)
```

### Registrar y actualizar el estado del documento

```python
from app.services.document_repository import get_document_repository

repo = get_document_repository()  # SupabaseDocumentRepository

# 1. Al recibir el archivo, antes de procesar: crea la fila en estado "processing"
record = repo.create_document(
    document_id="un-uuid-de-documento",
    title="Manual OCI",
    source_filename="manual_oci.pdf",
    object_key=object_key,
    user_id=None,
)
print(record.status)  # "processing"

# 2. Si la ingesta + indexado terminan bien:
repo.mark_ready(document_id="un-uuid-de-documento", total_parents=12, total_children=48)

# 3. Si algo falla en cualquier paso del pipeline:
repo.mark_failed(document_id="un-uuid-de-documento", error_message="Fallo al generar embeddings: ...")

# 4. Consultar un documento puntual
doc = repo.get_document("un-uuid-de-documento")
if doc is None:
    print("No existe")
else:
    print(doc.status, doc.total_children)

# 5. Listar documentos (sin login: devuelve todos; con login, filtra por user_id)
todos = repo.list_documents()
de_un_usuario = repo.list_documents(user_id="uuid-del-usuario")
```

### Por qué son dos archivos separados

- **`document_storage_service.py`**: mueve *bytes* del archivo original. No sabe nada de títulos ni de estados.
- **`document_repository.py`**: guarda *metadata* (título, `object_key`, estado). No sabe nada de cómo se sube o descarga el archivo — solo guarda la referencia (`object_key`) que le da el otro.

Esta separación es la misma razón por la que `document_pipeline_service.py` (el orquestador, pendiente) los usará a los dos por separado, uno para el archivo y otro para su estado, en vez de mezclar responsabilidades en un solo servicio.

---

## 3. Cuándo cambia esto (OCI, en el futuro)

Ambos archivos exponen una fábrica (`get_document_storage()`, `get_document_repository()`) que elige la implementación según `settings.STORAGE_METHOD`. Hoy solo existe la rama `"supabase"`. Cuando haya una cuenta de OCI y se revise `oci_storage_service.py` de los compañeros, se agregará una implementación `OCIDocumentStorage` detrás de la misma interfaz `BaseDocumentStorage`, sin tocar `document_pipeline_service.py` ni el resto del código que ya depende de estas fábricas.