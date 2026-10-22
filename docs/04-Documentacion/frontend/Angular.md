# Frontend Angular

> `docs/04-Documentacion/frontend/` · [Volver al README](../../../README.md)

Interfaz principal de NuevaMente: una SPA en **Angular 17** (TypeScript) que
consume la API REST del backend. Vive en `frontend/`.

---

## 1. Explicación simple: ¿qué es?

Es la aplicación con la que la persona usuaria sube documentos, revisa el
pipeline y explora los contenidos educativos generados (flashcards, quizzes,
tutoriales…). Se compone en rutas protegidas por un *guard* de autenticación.

---

## 2. Estructura

```text
frontend/src/
├── main.ts                 # bootstrapApplication (standalone)
├── environments/           # environment.ts / environment.prod.ts
└── app/
    ├── app.routes.ts       # definición de rutas
    ├── core/
    │   ├── api/            # servicios de acceso a la API
    │   ├── config/         # tokens de configuración
    │   ├── guards/         # authGuard / guestGuard
    │   ├── interceptors/   # interceptores HTTP
    │   ├── models/         # tipos compartidos
    │   ├── services/       # servicios de dominio
    │   ├── store/          # estado (auth, etc.)
    │   └── utils/          # helpers compartidos
    └── features/           # pantallas por dominio
        ├── auth/           # login, registro, recuperación
        ├── workspace/      # flujo de adaptación en pasos
        ├── process/        # progreso del procesamiento (SSE)
        ├── documents/      # subida y estado de documentos
        ├── library/        # biblioteca de contenidos generados
        ├── compare/        # comparación de variantes
        ├── shared/         # componentes reutilizables
        └── trash/          # papelera
```

> `src/app/app.module.ts` es código muerto: el bootstrap es *standalone*
> (`bootstrapApplication` en `src/main.ts`).

---

## 3. Rutas principales

| Ruta | Componente | Acceso |
| :--- | :--- | :--- |
| `/auth/login` | `LoginComponent` | Público (`guestGuard`) |
| `/auth/register` | `LoginComponent` (modo registro) | Público |
| `/auth/verify` | `LoginComponent` (verificación) | Público |
| `/auth/forgot` | `LoginComponent` (recuperación) | Público |
| `/auth/reset` | `LoginComponent` (nueva contraseña) | Público |
| `/terms`, `/privacy`, `/404` | `LoginComponent` | Público |
| `/workspace` | `WorkspaceComponent` | Protegido (`authGuard`) |
| `/documents` | `DocumentsComponent` (lazy) | Protegido |
| `/proceso` | `ProcessViewComponent` (lazy) | Protegido |
| `/library` | `LibraryComponent` | Protegido |
| `/papelera` | `TrashComponent` (lazy) | Protegido |
| `''`, `/**` | redirige a `/auth/login` | — |

---

## 4. Cómo ejecutarlo

```bash
cd frontend
npm install
npm start          # ng serve en http://localhost:4200
```

Para verificar que compila:

```bash
npm run build
```

Pruebas unitarias (Karma + Jasmine, Chrome headless):

```bash
npm run test:ci
```

---

## 5. Integración con el backend

- La app consume `HttpNuevaMenteApiService` (token `NUEVAMENTE_API`) desde
  `src/app/core/api/http-nuevamente-api.service.ts`.
- La URL base se resuelve así: en `localhost`/`127.0.0.1` usa
  `environment.apiUrl` (`/api/v1`, relativa); en cualquier otro host usa `/api`.
  En desarrollo, `proxy.conf.json` redirige `/api` a
  `http://127.0.0.1:8001` (el `APP_PORT` por defecto del backend).
- Si `environment.useMock` es `true`, el servicio cae a
  `MockNuevaMenteApiService`; hoy es `false`, pero el fallback silencioso ante
  errores sigue activo: **revisa la consola del navegador** para detectar el
  aviso antes de confiar en la UI.
- La ingesta se hace con `fetch` sobre `POST /documents?stream=true` para
  consumir el stream de progreso (SSE).
- El login de desarrollo está *mockeado* mientras
  `environment.enableDemoLogin` sea `true`: usuario demo
  `ana.martinez@empresa.com` / `Password123!` (lo maneja `MockAuthApiService`, no
  FastAPI).
- En producción (`environment.prod.ts`), el frontend se sirve detrás del proxy de
  nginx (`frontend/nginx.conf`), que redirige `/api/` al backend. Revisa que
  `apiUrl` no duplique el prefijo `/api`.

### Limitación conocida con Supabase parcial

La SPA **no está adaptada** al modo Supabase parcial (solo documentos originales
y metadata). El motivo es el modelo de identidad:

- Los usuarios de SQLite usan IDs como `usr_ana_001`, `usr_diego_002`, etc.
- En Supabase, `documents.user_id` es de tipo `uuid`.
- `SupabaseDocumentRepository` valida el UUID antes de consultar
  (`_require_valid_uuid`).

Por eso, con un usuario autenticado en Angular, listar o subir documentos falla.
Para probar el modo Supabase parcial usa [Gradio](Gradio.md), que llama al
pipeline con `user_id=None`. La adaptación de autenticación y frontend está en
[Mejoras Post-MVP](../../05-Roadmap/Mejoras_Post_MVP.md).

---

## 6. Interfaz alternativa de pruebas

Para pruebas rápidas del pipeline sin la SPA existe una UI mínima en Gradio →
ver [Gradio](Gradio.md).

---

<div align="right">

[Volver al README](../../../README.md)

</div>

