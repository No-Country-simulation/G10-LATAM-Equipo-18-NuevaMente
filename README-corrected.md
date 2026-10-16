# NuevaMente — Sistema Inteligente de Adaptación y Generación de Contenido Educativo

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11+-green.svg)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)
![Angular](https://img.shields.io/badge/Frontend-Angular%2017+-DD0031.svg)
![Google Gemini](https://img.shields.io/badge/AI-Google%20Gemini%201.5%2F2.0-8E44AD.svg)
![Groq](https://img.shields.io/badge/AI-Groq-red)
[![OpenRouter](https://shields.io)](https://openrouter.ai)
![Oracle Cloud](https://img.shields.io/badge/Cloud-OCI%20Always%20Free-F80000.svg)

**NuevaMente** transforma documentación técnica en materiales educativos claros y didácticos, permitiendo que los equipos aceleren el aprendizaje a partir del conocimiento técnico ya existente.

## Índice

- [1. Descripción del proyecto](#1-descripción-del-proyecto)
- [2. Características principales](#2-características-principales)
- [3. Arquitectura y tecnologías](#3-arquitectura-y-tecnologías)
- [4. Acceso al proyecto / Instalación](#4-acceso-al-proyecto--instalación)
- [5. Uso](#5-uso)
- [6. Estructura del proyecto](#6-estructura-del-proyecto)
- [7. Documentación detallada](#7-documentación-detallada)
- [8. Próximos pasos o futuras implementaciones](#8-próximos-pasos-o-futuras-implementaciones)
- [9. Contribución](#9-contribución)
- [10. Licencia](#10-licencia)

## 1. Descripción del proyecto

**Problema:** Las organizaciones acumulan manuales, guías, especificaciones y otra documentación técnica extensa, pero este conocimiento suele ser difícil de asimilar para quienes están en proceso de formación u onboarding. Ese material, por su densidad y formato, queda infrautilizado.

**Solución:** NuevaMente toma esa documentación existente y la adapta a contenido educativo estructurado, ajustado al perfil y nivel de detalle, sin perder precisión ni fidelidad a la fuente.

**Valor:** Reduce el tiempo de aprendizaje, facilita la transferencia de conocimiento dentro del equipo y reutiliza activos técnicos ya existentes para generar material formativo útil y listo para aplicar.

**Público objetivo:** Equipos de formación, producto, desarrollo y documentación que necesitan convertir activos técnicos en materiales de aprendizaje para acelerar la adopción de tecnologías, herramientas o procesos.

**Enfoque actual:** El flujo se basa en **recuperación vectorial + adaptación con LLM**. Se obtiene contexto relevante mediante búsqueda por similitud semántica (vectorial) y se adapta ese contexto al formato educativo mediante un LLM. El sistema está diseñado para priorizar la fidelidad a las fuentes y cuenta con **cascada de proveedores con fallback** para mejorar su robustez.

**Más información →** [docs/01-Arquitectura/Arquitectura.md](docs/01-Arquitectura/Arquitectura.md)

## 2. Características principales

- **Adaptación educativa flexible**: Soporta múltiples formatos (Flashcards, Quiz, Tutorial, Resumen Ejecutivo, Guión de Clase) según el objetivo de aprendizaje.
- **Recuperación vectorial**: Búsqueda semántica por similitud sobre **FAISS** (local) con control total sobre los datos.
- **Adaptación guiada por prompts**: Prompts externos para ajustar tono, formato y nivel de detalle sin modificar el código.
- **Robustez con fallback**: Implementación preparada para **cascada de modelos con fallback** entre proveedores, lo que permite mantener la disponibilidad ante errores o límites.
- **API REST organizada (FastAPI)**: Endpoints claros para ingesta, recuperación y adaptación.
- **Interfaz web (Angular 17)**: UI principal para probar y visualizar el flujo completo.
- **Alternativa básica para pruebas rápidas (Gradio)**: Incluye una interfaz ligera basada en **Gradio** para validar ingesta y generación sin levantar el frontend completo.

**Más información →** [docs/01-Arquitectura/Componentes.md](docs/01-Arquitectura/Componentes.md)

## 3. Arquitectura y tecnologías

```mermaid
flowchart LR
  A[Documentación técnica] --> B[Ingesta]
  B --> C[Segmentación en chunks]
  C --> D[Generación de embeddings]
  D --> E[(Vector Store\nFAISS)]
  E --> F[Recuperación vectorial\n(Búsqueda por similitud semántica)]
  F --> G[Adaptación con LLM\n(Cascada + Fallback)]
  G --> H[Contenido educativo estructurado]
  H --> I[Frontend Angular 17]
  K[API REST - FastAPI] <---> I
  K <---> G
  G --> L[(Persistencia\nOCI / SQLite)]
```

- **Backend:** FastAPI (Python >= 3.11), gestionado con [uv](https://github.com/astral-sh/uv).
- **Frontend:** Angular 17 (standalone), servido con nginx.
- **Vector Store:** FAISS (local)
- **Embeddings:** Gemini, Jina y modelo local (`intfloat/multilingual-e5-base`).
- **LLM:** Google Gemini (modelo principal), con soporte para **cascada y fallback** entre proveedores.
- **Orquestación:** LangGraph con Multi-Agent.
- **Almacenamiento:** OCI Object Storage (Always Free) + SQLite local para metadatos, alternativa Supabase, o local.

**Más información →** [docs/01-Arquitectura/Tecnologias.md](docs/01-Arquitectura/Tecnologias.md)

## 4. Acceso al proyecto / Instalación

**Pasos rápidos:**

1. Clonar el repositorio
2. Configurar el backend con `uv` (no usar `requirements.txt`: está desactualizado)
3. Configurar el frontend con `npm`
4. Crear `backend/.env` a partir de `backend/.env.example`
5. Ejecutar backend y frontend

**Guía paso a paso →** [docs/02-Instalacion/Uso_Local.md](docs/02-Instalacion/Uso_Local.md)  
(Configuración de LLMs y de almacenamiento en la misma carpeta `02-Instalacion/`)

## 5. Uso

- **Backend (desarrollo):** Desde `backend/`
  ```bash
  uv run --with email-validator --with genanki uvicorn main:app --reload
  ```
- **Frontend (desarrollo):** Desde `frontend/`
  ```bash
  npm install && npm start  # http://localhost:4200
  ```
- **Alternativa básica para pruebas rápidas (Gradio):** Desde `backend/`
  ```bash
  uv run python ../frontend_gradio/app_gradio.py
  ```
  > `frontend_gradio/` es una **alternativa básica** (UI con Gradio) pensada para validaciones puntuales del flujo de ingesta/adaptación, sin necesidad de levantar la aplicación Angular completa.

**Más información →** [docs/02-Instalacion/Uso_Local.md](docs/02-Instalacion/Uso_Local.md) | [API de Ingesta](docs/04-Documentacion/backend/ingestion/API_de_Ingesta.md)

## 6. Estructura del proyecto

```text
nueva-mente/
├── backend/            # API FastAPI (Python >= 3.11)
│   ├── app/             # Núcleo: api/, core/, services/, prompts/, schemas/, infrastructure...
│   ├── migrations/      # Migraciones SQL (aplicadas manualmente en Supabase)
│   ├── scripts/         # Scripts de apoyo y diagnóstico
│   └── tests/           # Pruebas del backend (pytest) y scripts en tests/manual/
├── frontend/           # Aplicación Angular 17 (standalone). UI principal
├── frontend_gradio/    # UI alternativa básica (Gradio) para pruebas rápidas
├── docs/               # Documentación detallada del proyecto (organizada por carpetas)
├── .gitignore          # Archivo de configuración de gitignore
└── .gitleaks.toml      # Configuración de detección de secretos
```

**Más información →** [docs/03-Estructura/Estructura_de_Archivos.md](docs/03-Estructura/Estructura_de_Archivos.md)

## 7. Documentación detallada

La documentación está organizada para facilitar el recorrido según el nivel de necesidad:

| Carpeta | Descripción |
|---|---|
| **[docs/01-Arquitectura/](docs/01-Arquitectura/)** | Arquitectura, componentes y tecnologías del sistema |
| **[docs/02-Instalacion/](docs/02-Instalacion/)** | Uso local y configuración de LLMs y de almacenamiento |
| **[docs/03-Estructura/](docs/03-Estructura/)** | Estructura de archivos del repositorio |
| **[docs/04-Documentacion/backend/](docs/04-Documentacion/backend/)** | Detalle técnico del backend: ingesta, embeddings, almacenamiento, recuperación y arquitectura |
| **[docs/04-Documentacion/frontend/](docs/04-Documentacion/frontend/)** | Frontend Angular y UI de pruebas con Gradio |
| **[docs/old/](docs/old/)** | Documentación archivada (revisión pendiente) |

> **Nota:** Las **pruebas del backend** viven en `backend/tests/` (suite con `pytest`) y `backend/tests/manual/` (scripts ejecutables). El README se mantiene conciso y enfocado.

## 8. Próximos pasos o futuras implementaciones

- **Solicitud de Temas o Secciones Específicas**: Adaptar el contenido de un tema o sección específico. 

## 9. Contribución

Este proyecto se desarrolla de forma **interna por el Equipo 18 del G10**. Para mantener coherencia, calidad y trazabilidad, se recomienda seguir estas directrices:

- Nombres

## 10. Licencia

Proyecto educativo. Ver detalles en [LICENSE](LICENSE).