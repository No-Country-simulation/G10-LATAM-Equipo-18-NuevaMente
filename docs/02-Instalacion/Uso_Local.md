# Uso Local

> 📍 `docs/02-Instalacion/` · [Volver al README](../../README.md)

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

> `requirements.txt` o
> `pyproject.toml` con `uv.lock`.

### Frontend

```bash
cd frontend
npm install
```

---

## 2. Ejecutar

### Backend (desde `backend/`)

```bash
uv run --with email-validator --with genanki uvicorn main:app --reload
```

- API: `http://localhost:8000`
- Documentación interactiva: `http://localhost:8000/docs`

> Las dos dependencias extra (`email-validator` y `genanki`) se pasan en la línea
> de comandos porque no están declaradas en `pyproject.toml`. Reinicia el backend
> después de cambiar código.

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
# Salud del sistema
curl http://localhost:8000/api/v1/health

# Listar documentos indexados
curl http://localhost:8000/api/v1/documents
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

> `tests/manual/` son scripts ejecutables, no pruebas de suite. `npm test` está
> roto actualmente; verifica el frontend con `npm run build`.

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

[⬆ Volver al README](../../README.md)

</div>
