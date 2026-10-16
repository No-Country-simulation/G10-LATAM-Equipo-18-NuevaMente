# Frontend Angular

> 📍 `docs/04-Documentacion/frontend/` · [Volver al README](../../../README.md)

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
    │   └── store/          # estado (auth, etc.)
    └── features/           # pantallas por dominio
        ├── auth/           # login, registro, recuperación
        ├── workspace/      # flujo de adaptación en pasos
        ├── documents/      # subida y estado de documentos
        ├── library/        # biblioteca de contenidos generados
        ├── compare/        # comparación de variantes
        └── trash/          # papelera
```

> `src/app/app.module.ts` es código muerto: el bootstrap es *standalone*
> (`bootstrapApplication` en `src/main.ts`).

---

## 3. Rutas principales

| Ruta | Componente | Acceso |
| :--- | :--- | :--- |
| `/auth/login` | `LoginComponent` | Público (`guestGuard`) |
| `/workspace` | `WorkspaceComponent` | Protegido (`authGuard`) |
| `/documents` | `DocumentsComponent` (lazy) | Protegido |
| `/library` | `LibraryComponent` | Protegido |
| `/papelera` | `TrashComponent` (lazy) | Protegido |
| `/**` | redirige a `/auth/login` | — |

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

> **`npm test` está roto:** faltan los paquetes de karma/jasmine en
> `devDependencies` y `tsconfig.spec.json` hereda `exclude: ["src/**/*.spec.ts"]`.
> Verifica los cambios con `npm run build`.

---

## 5. Integración con el backend

- La app consume `HttpNuevaMenteApiService` (token `NUEVAMENTE_API`) desde
  `src/app/core/api/http-nuevamente-api.service.ts`.
- La URL base se resuelve así: si la app corre en `localhost`/`127.0.0.1`, usa
  `environment.apiUrl` (`http://localhost:8001/api/v1`); en cualquier otro host,
  usa la ruta relativa `/api` (que nginx traduce al backend).
- Si `environment.useMock` es `true`, el servicio cae a
  `MockNuevaMenteApiService`; hoy es `false`, así que **revisa la consola del
  navegador** para detectar el aviso de fallback antes de confiar en la UI.
- La ingesta se hace con `fetch` sobre `POST /documents?stream=true` para
  consumir el stream de progreso (SSE).
- El login de desarrollo está *mockeado* mientras
  `environment.enableDemoLogin` sea `true`: usuario demo
  `ana.martinez@empresa.com` / `Password123!` (lo maneja `MockAuthApiService`, no
  FastAPI).
- En producción (`environment.prod.ts`), el frontend se sirve detrás del proxy de
  nginx (`frontend/nginx.conf`), que redirige `/api/v1/` al backend.

---

## 6. Interfaz alternativa de pruebas

Para pruebas rápidas del pipeline sin la SPA existe una UI mínima en Gradio →
ver [Gradio](Gradio.md).

---

<div align="right">

[⬆ Volver al README](../../../README.md)

</div>
