# Uso Local

> `docs/02-Instalacion/` · [Volver al README](../../README.md)

Guía paso a paso para levantar NuevaMente en tu máquina: backend, frontend y la
interfaz de pruebas.

---

## 0. Requisitos

- **Python 3.12+** y [**uv**](https://docs.astral.sh/uv/).
- **Node.js 18+** y **npm** (para el frontend).
- Claves de API (Gemini, Jina…) si quieres usar los proveedores en la nube
  (si no, el sistema cae al modelo local donde aplique).

---

## 1. Clonar e instalar

```bash
git clone <url-del-repositorio>
cd NuevaMente
```

### Backend

```bash
cd backend
uv sync
cp .env.example .env    # Windows PowerShell: Copy-Item .env.example .env
# Edita .env con tus claves (ver 02-Instalacion/Configuracion_de_LLMs.md)
```

> `uv` es la fuente de verdad: usa `pyproject.toml` y `uv.lock`. El archivo
> `requirements.txt` se regenera con `uv export` y solo lo usa la imagen Docker.

### Frontend

```bash
cd frontend
npm install
```

---

## 2. Ejecutar

### Backend (desde `backend/`)

```bash
uv run --with email-validator --with genanki python main.py
```

- API: `http://localhost:8001` (o el puerto configurado en `APP_PORT` dentro de `backend/.env`)
- Documentación interactiva: `http://localhost:8001/docs`

> Al ejecutar `python main.py`, el servidor toma automáticamente el host y puerto definidos en `config.py` y los sobrescribe con la variable de entorno `APP_PORT` de tu `.env` (por defecto `8001`).
> Las dependencias `email-validator` y `genanki` se encuentran declaradas en `pyproject.toml` y en `requirements.txt`.

#### Elegir el puerto (`APP_PORT`)

```bash
# backend/.env
APP_PORT=8001
```

- Con `APP_PORT=8001` (valor por defecto) el backend evita el `8000` y el
  frontend de desarrollo ya hace proxy a `http://127.0.0.1:8001`.
- Si tienes **otra aplicación usando el 8000**, no cambies nada: usa `8001`.
- Si prefieres el **8000**, pon `APP_PORT=8000` y cambia también el destino en
  `frontend/proxy.conf.json`.
- En **Docker** el contenedor escucha en `8000`; el mapeo al host está en
  `docker-compose.yml` (ver [Despliegue Docker](Despliegue_Docker_OCI.md)).

### Frontend (desde `frontend/`)

```bash
npm start        # ng serve en http://localhost:4200
```

### Interfaz de pruebas Gradio (desde `backend/`)

```bash
uv run python ../frontend_gradio/app_gradio.py
```

Abre la URL local que imprime la consola (`http://127.0.0.1:7860`).

---

## 3. Verificar que todo funciona

```bash
# Salud del sistema (ajusta el puerto a tu APP_PORT; por defecto 8001)
curl http://localhost:8001/api/v1/health

# Listar documentos indexados
curl http://localhost:8001/api/v1/documents
```

Comprobación de servicios externos:

```bash
cd backend
uv run python scripts/check_services.py
```

---

## 4. Pruebas

```bash
cd backend
uv run --with pytest --with email-validator --with genanki pytest tests/test_phase0_health.py tests/test_embedding_service.py tests/test_ingester_service.py
```

Frontend (Karma + Jasmine, ejecución única en Chrome headless):

```bash
cd frontend
npm run test:ci
```

> `tests/manual/` son scripts ejecutables, no pruebas de suite. Pasa siempre
> rutas explícitas a `pytest`: una ejecución sin argumentos también recoge
> `scratch/`.

---

## 5. Problemas comunes

| Síntoma | Causa / solución |
| :--- | :--- |
| El backend falla al importar | Falta `--with email-validator --with genanki` en el comando `uv run`. |
| La UI parece funcionar sin backend | El frontend cayó a `MockNuevaMenteApiService`. Revisa la consola del navegador. |
| Errores de cuota en embeddings | Revisa las claves y los límites → [Configuración de LLMs](Configuracion_de_LLMs.md). |
| No se guardan documentos | Revisa `STORAGE_METHOD` y credenciales → [Configuración de Storages](Configuracion_de_Storages.md). |

---

<div align="right">

[Volver al README](../../README.md)

</div>

