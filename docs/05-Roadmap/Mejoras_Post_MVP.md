# Mejoras Post-MVP y Deuda Técnica

> `docs/05-Roadmap/` · [Volver al README](../../README.md)

Este documento concentra las capacidades que **no forman parte del MVP
entregado** y que hoy aparecen mencionadas en la arquitectura, la configuración
o el código como trabajo futuro. Su objetivo es evitar que la documentación
prometa un reemplazo total de proveedor cuando el sistema todavía no lo ofrece.

---

## 1. Estado actual (punto de partida)

| Capacidad | Estado en el MVP | Observación |
| :--- | :--- | :--- |
| Documentos originales | OCI, Supabase parcial o disco local | Supabase está implementado para el archivo original y su metadata. |
| Metadata de documentos | Supabase o SQLite | Depende del backend resuelto para documentos. |
| Artefactos generados (JSON/PDF) | OCI o disco local | La ruta de Supabase existe en código, pero **no está conectada** a la cola de persistencia. |
| Biblioteca y papelera | SQLite | `contenidos`, `audit_log` y `storage_jobs` viven en `users.db`. |
| Autenticación y usuarios | SQLite | IDs del tipo `usr_ana_001`, no UUID. |
| Persistencia vectorial | FAISS local por documento | No se guarda en OCI ni en Supabase. |
| Selector de backend | Variables de entorno | No existe panel de administración ni validación desde la UI. |
| Frontend Angular | Angular + API REST | No está adaptado al modo Supabase parcial por el modelo de usuarios. |
| UI recomendada para Supabase parcial | Gradio | No requiere login y usa `user_id=None`. |

> **Regla de documentación:** mientras este documento siga vigente, no debe
> afirmarse que “Supabase reemplaza a OCI” de forma completa. El alcance real es
> **Supabase parcial para documentos originales y su metadata**.

---

## 2. Panel de configuración de almacenamiento

### Objetivo

Permitir que un administrador elija, valide y cambie el destino de cada tipo de
dato sin editar `.env` ni reiniciar el backend a ciegas.

### Alcance propuesto

| Tipo de dato | Opciones deseadas | Estado actual |
| :--- | :--- | :--- |
| Documentos originales | OCI, Supabase, local (solo desarrollo) | Configurable por `.env`. |
| Adaptaciones y artefactos | OCI, Supabase, local (solo desarrollo) | Solo OCI/local. |
| Metadata de documentos | Supabase/Postgres o SQLite | Depende del backend de documentos. |
| Contenidos, auditoría y cola | Supabase/Postgres o SQLite | Solo SQLite. |
| Vectores | FAISS local, FAISS persistido en objeto, pgvector | Solo FAISS local. |

### Requisitos funcionales

- Elegir backend **por tipo de dato**, no un único interruptor global.
- Probar conexión antes de guardar (bucket, permisos, tabla, credenciales).
- Mostrar el backend efectivo y si hubo un fallback.
- Gestionar credenciales de forma segura (nunca exponer `service_role` al
  frontend).
- Registrar auditoría de cambios: quién, cuándo, valor anterior y nuevo.
- Definir precedencia entre panel y variables de entorno.
- Indicar si el cambio requiere migración de datos o reinicio.
- Validar que el backend elegido soporta la operación (por ejemplo, no aceptar
  Supabase para artefactos hasta que exista el backend correspondiente).

### Fuera del MVP

- Interfaz de administración en Angular.
- Persistencia cifrada de credenciales.
- Migración automática entre backends.
- Edición de configuración en caliente sin reinicio.

### Criterios de aceptación

1. Un administrador puede guardar un backend por tipo de dato.
2. El backend rechaza una configuración inválida con un mensaje claro.
3. La UI muestra el backend efectivo y el último chequeo de salud.
4. Los cambios quedan auditados.
5. Los tests cubren selección, validación y fallback.

---

## 3. Integración completa con Supabase

### Objetivo

Que Supabase pueda usarse como proveedor completo sin depender de OCI ni de
SQLite para el flujo principal.

### Trabajo pendiente

1. **Backend de artefactos en Supabase**
   - Implementar un `StorageBackend` de Supabase para la cola de persistencia.
   - Usar `SUPABASE_BUCKET_ARTIFACTS`.
   - Corregir `SupabaseStorageService.upload_json_artifact()` para que no
     devuelva `completado` cuando la subida falla.
2. **Metadata de contenidos en Supabase**
   - Migrar `contenidos` a Postgres o crear un repositorio equivalente.
   - Decidir el destino de `002_adapted_contents.sql` (usarla o retirarla).
3. **Cola y papelera**
   - Hacer que `StorageQueueService` y `TrashService` usen el backend resuelto,
     no OCI de forma directa.
   - Evitar que la papelera reporte éxito y deje archivos huérfanos.
4. **Autenticación**
   - Migrar usuarios a Supabase Auth o mapear los IDs `usr_*` a UUID.
   - Ajustar la validación de `documents.user_id`.
5. **Seguridad**
   - Activar RLS cuando el frontend consulte Supabase directamente.
   - Mantener `service_role` solo en el backend.
6. **Pruebas**
   - Tests de integración contra un proyecto Supabase de pruebas.
   - Tests de fallback y de error de credenciales.

### Criterios de aceptación

- Un documento original y su artefacto generado quedan en Supabase.
- La biblioteca y la papelera funcionan sin SQLite.
- Un usuario autenticado puede subir, listar y borrar documentos.
- No hay rutas que usen OCI si el backend activo es Supabase.

---

## 4. Persistencia vectorial

### Situación actual

FAISS se guarda en disco (`vector_store/{document_id}/`) y se pierde si no se
conserva el volumen. La configuración `VECTOR_STORE_METHOD` menciona `pgvector`,
pero **no hay implementación**.

### Opciones a evaluar

1. **FAISS persistido en Object Storage**
   - Subir `index.faiss` y `metadata.json` a OCI o Supabase.
   - Descargarlos al procesar un documento.
   - Menor cambio, pero sigue siendo un índice por documento.
2. **pgvector en Supabase/Postgres**
   - Tabla de chunks con embedding y metadata.
   - Búsqueda por similitud desde SQL.
   - Requiere migración de los índices actuales.
3. **Motor vectorial administrado**
   - Qdrant, Pinecone u otro.
   - Evaluar costo, latencia y complejidad operativa.

### Requisitos

- Definir si el vector store es por documento o global.
- Versionar el modelo de embeddings y la dimensión.
- Incluir reindexación y migración desde FAISS.
- Medir latencia y costo antes de elegir.

---

## 5. Migración de autenticación y frontend

### Limitación actual

- Los usuarios de SQLite usan IDs `usr_ana_001`, `usr_diego_002`, etc.
- La tabla `documents` de Supabase espera `user_id uuid`.
- `SupabaseDocumentRepository` valida UUID antes de consultar.
- Por eso el frontend Angular no puede listar ni subir documentos en modo
  Supabase parcial; Gradio sí, porque usa `user_id=None`.

### Trabajo pendiente

- Migrar autenticación a Supabase Auth o crear una tabla de mapeo
  `usuario_local → uuid`.
- Cambiar el tipo de `documents.user_id` si se decide mantener IDs de texto.
- Adaptar Angular para mostrar el backend activo y los estados de persistencia.
- Unificar biblioteca y papelera con el backend de contenidos elegido.

---

## 6. Migración y operación de datos

- Script de migración OCI → Supabase para documentos originales.
- Script de migración local/SQLite → Supabase para metadata y contenidos.
- Verificación por checksum y conteo de objetos.
- Modo `dry-run` y plan de rollback.
- Documentar ventanas de mantenimiento y respaldo previo.

---

## 7. Observabilidad y seguridad

- Endpoint de salud por backend: documentos, artefactos, metadata y vectores.
- Estado de la cola (`storage_jobs`) visible para administración.
- Alertas por fallos de subida, cuotas y credenciales vencidas.
- Auditoría de cambios de configuración.
- Revisión de RLS, políticas de bucket y rotación de claves.
- Nunca registrar `SUPABASE_KEY`, `OCI_*` ni tokens en logs.

---

## 8. Pruebas y documentación

- Tests de contrato para `StorageBackend` y repositorios.
- Tests de integración con un proyecto Supabase de pruebas.
- Tests de regresión para el modo OCI y el modo local.
- Actualizar esta guía cuando una capacidad pase a implementada.
- Mantener la matriz de compatibilidad de
  [Configuración de Storages](../02-Instalacion/Configuracion_de_Storages.md)
  sincronizada con el código.

---

## 9. Priorización sugerida

| Prioridad | Mejora | Depende de |
| :--- | :--- | :--- |
| P1 | Backend Supabase para artefactos + cola + papelera | Nada |
| P1 | Metadata de contenidos en Supabase | P1 anterior |
| P1 | Mapeo de usuarios / auth para Supabase | Definición de identidad |
| P1 | Panel de configuración de almacenamiento | Backends por tipo de dato |
| P2 | Persistencia vectorial (FAISS remoto o pgvector) | Definición de arquitectura |
| P2 | Migración automatizada de datos | P1 de Supabase |
| P2 | Observabilidad y salud por backend | Panel de configuración |
| P3 | RLS y acceso directo del frontend a Supabase | Auth en Supabase |

---

## 10. Lo que el MVP no promete

Para evitar malentendidos en la entrega:

- No hay reemplazo total de OCI por Supabase.
- No hay panel de configuración de almacenamiento.
- No hay persistencia de vectores en Supabase.
- No hay migración automática de documentos ni contenidos.
- El frontend Angular no está adaptado al modo Supabase parcial.
- Gradio es la interfaz recomendada para probar ese modo.

---

<div align="right">

[Volver al README](../../README.md)

</div>
