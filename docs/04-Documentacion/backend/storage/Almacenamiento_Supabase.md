# Almacenamiento de Documentos con Supabase

> `docs/04-Documentacion/backend/storage/` · [Volver al README](../../../../README.md)

## Alcance actual: modo parcial

Supabase está implementado para **documentos originales y su metadata**. No es
un reemplazo completo de OCI.

| Elemento | ¿Se guarda en Supabase? |
| :--- | :--- |
| Archivo original (PDF/MD/TXT) | Sí, bucket `document-source` |
| Metadata del documento (`documents`) | Sí, Postgres/Supabase |
| JSON de adaptaciones generadas | **No**; va a OCI o `storage_mock/` |
| Biblioteca y papelera (`contenidos`) | **No**; sigue en SQLite |
| Vectores FAISS | **No**; siguen en disco local |
| Usuarios y autenticación | **No**; siguen en SQLite |

> Supabase no usa SQLite. La tabla `documents` y el bucket `document-source`
> viven en Supabase/Postgres; SQLite solo conserva las tablas del MVP que aún no
> se migraron (usuarios, contenidos, papelera y cola).

El reemplazo total está planificado en
[Mejoras Post-MVP](../../../05-Roadmap/Mejoras_Post_MVP.md).

---

## 1. Configuración manual (una sola vez)

### 1.1 Crear el bucket de documentos

1. En [supabase.com](https://supabase.com) entra a tu proyecto → **Storage**.
2. Crea un bucket privado llamado `document-source`.
3. No lo marques como público: el backend usa `service_role` y no necesita
   exponerlo.

El bucket `adapted-artifacts` puede crearse para la futura integración de
artefactos, pero **el flujo actual no lo usa**.

### 1.2 Crear las tablas

En **SQL Editor** aplica, en este orden:

1. `migrations/001_documents.sql`
2. `migrations/003_documents_storage_backend.sql`

> **No apliques `002_trash_system.sql` en Supabase.** Esa migración modifica la
> tabla `contenidos`, que existe en SQLite pero no en Supabase.
>
> `002_adapted_contents.sql` existe, pero hoy no la usa ningún servicio. No es
> necesaria para el modo parcial.

### 1.3 Credenciales

En **Project Settings → API**:

- **Project URL** → `SUPABASE_URL`
- **service_role key** → `SUPABASE_KEY` (nunca la `anon/public`)

### 1.4 Variables de entorno

```dotenv
# backend/.env — nunca se sube a git
APP_ENV=development
STORAGE_METHOD=supabase
SUPABASE_URL=https://tuproyecto.supabase.co
SUPABASE_KEY=eyJh...              # service_role
SUPABASE_BUCKET_DOCUMENTS=document-source
SUPABASE_BUCKET_ARTIFACTS=adapted-artifacts
ALLOW_LOCAL_STORAGE=true          # artefactos en storage_mock/ mientras no haya backend Supabase
```

### 1.5 Dependencia

`supabase` ya está declarado en `pyproject.toml` y `uv.lock`, así que `uv sync`
lo instala.

---

## 2. Uso en código

### 2.1 Pipeline recomendado

```python
from app.services.document_pipeline_service import process_and_index_document

record = process_and_index_document(
    local_path="/tmp/manual.pdf",
    title="Manual",
    user_id=None,   # Gradio usa None; Angular envía usr_* y no es compatible
)

print(record.status)  # ready | failed
```

### 2.2 Subir y descargar el archivo original

```python
from app.services.document_storage_service import get_document_storage

storage = get_document_storage()  # SupabaseStorageService si el backend resuelto es supabase

object_key = storage.upload_document(
    local_path="/tmp/manual.pdf",
    user_id=None,
    document_id="un-uuid-de-documento",
)

local_path = storage.download_document(
    object_key=object_key,
    destination_path="/tmp/reprocesar/manual.pdf",
)
```

### 2.3 Metadata del documento

```python
from app.services.document_repository import get_document_repository

repo = get_document_repository()  # SupabaseDocumentRepository en modo supabase

record = repo.create_document(
    document_id="un-uuid-de-documento",
    title="Manual",
    source_filename="manual.pdf",
    object_key=object_key,
    user_id=None,
)

repo.mark_ready("un-uuid-de-documento", total_parents=12, total_children=48)
repo.mark_failed("un-uuid-de-documento", error_message="Fallo de embeddings")
```

`document_storage_service.py` mueve bytes; `document_repository.py` guarda
metadata y estados. `document_pipeline_service.py` coordina ambos.

---

## 3. Compatibilidad

### Gradio: sí

Gradio llama al pipeline con `user_id=None`, por lo que funciona con Supabase
parcial. Es la interfaz recomendada para probar este modo:

```powershell
cd backend
uv run python ../frontend_gradio/app_gradio.py
```

Ver [Frontend Gradio](../../frontend/Gradio.md).

### Angular: no en modo Supabase parcial

- Los usuarios de SQLite usan IDs como `usr_ana_001`.
- `documents.user_id` en Supabase es `uuid`.
- `SupabaseDocumentRepository` valida UUID antes de consultar.

Por eso, con un usuario autenticado en Angular, listar o subir documentos falla.
La adaptación está en el roadmap. Ver
[Frontend Angular](../../frontend/Angular.md).

### Artefactos generados: no

`StorageQueueService` sigue usando OCI o disco local. El método
`SupabaseStorageService.upload_json_artifact()` existe, pero no está conectado y
hoy devuelve `completado` incluso si la subida falla. No lo uses como base para
producción sin corregirlo.

---

## 4. Verificación

1. Ejecuta `uv run --with email-validator --with genanki python -c "from app.core.config import settings; print(settings.resolve_storage_backend())"`.
2. Sube un documento desde Gradio.
3. Revisa el objeto en el bucket `document-source`.
4. Revisa la fila en la tabla `documents`.
5. Confirma que el artefacto generado **no** está en Supabase; estará en OCI o
   `storage_mock/`.

Si falla la subida:

- Revisa que `SUPABASE_KEY` sea `service_role`.
- Revisa que el bucket exista y sea privado.
- Revisa que aplicaste `001` y `003`.
- Revisa que `STORAGE_METHOD=supabase` y que las credenciales no estén vacías.

---

## 5. Relación con OCI

Puedes usar Supabase para documentos originales y mantener OCI para artefactos.
En ese caso OCI sigue siendo necesario y no se está reemplazando por completo.
La configuración de ambos modos está en
[Configuración de Storages](../../../02-Instalacion/Configuracion_de_Storages.md).

---

<div align="right">

[Volver al README](../../../../README.md) · [Mejoras Post-MVP](../../../05-Roadmap/Mejoras_Post_MVP.md)

</div>
