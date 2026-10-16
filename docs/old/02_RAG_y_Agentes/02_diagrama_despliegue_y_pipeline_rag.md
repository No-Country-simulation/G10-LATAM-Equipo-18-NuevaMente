# 🚀 Documentación 2: Diagrama de Despliegue y Pipeline RAG Avanzado

> **Sistema Inteligente de Adaptación y Generación de Contenido Educativo**  
> *Hackathon ONE G10 — Oracle Next Education & Alura | Grupo 10*

---

## 1. Diagrama de Despliegue (Deployment Diagram)

El esquema de despliegue de **NuevaMente** está optimizado para funcionar en entornos de desarrollo local y en la nube de **Oracle Cloud Infrastructure (OCI)** dentro de la capa **Always Free**, garantizando cero costo operativo y alta concurrencia.

```mermaid
deploymentDiagram
    node "Cliente - Navegador Web" {
        component [Angular 18 SPA] as Frontend
        component [Estilos CSS / PDF Exporter] as PDFEngine
    }

    node "Servidor de Aplicación (Host Local / OCI VM)" {
        node "Entorno Python FastAPI (ASGI Uvicorn)" {
            component [FastAPI REST Router] as APIRouter
            component [Agent Orchestrator (LangGraph)] as Orchestrator
            component [FAISS Vector Index (CPU)] as VectorIndex
            component [Graph RAG DAG Manager] as GraphEngine
        }
    }

    node "Google Cloud AI" {
        component [Google Gemini 1.5 Pro / Flash API] as GeminiAPI
    }

    node "Oracle Cloud Infrastructure (OCI)" {
        node "OCI Object Storage (Always Free)" {
            database [Bucket: nuevamente-contenidos-educativos] as OCIBucket
        }
    }

    Frontend --> APIRouter : HTTP / REST (Port 8000)
    APIRouter --> Orchestrator : Invoca Pipeline
    Orchestrator --> VectorIndex : Consultas Híbridas (FAISS + BM25)
    Orchestrator --> GraphEngine : Recorrido DAG (Prerrequisitos)
    Orchestrator --> GeminiAPI : HTTPS / JSON Schema (API Key)
    Orchestrator --> OCIBucket : OCI SDK (Upload Artifacts)
```

---

## 2. Explicación Paso a Paso de la Topología de Despliegue

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                           PASO A PASO DEL DESPLIEGUE                          │
└───────────────────────────────────────────────────────────────────────────────┘

 1. NODO CLIENTE (Navegador Web):
    - Ejecuta el cliente Angular 18 compilado en modo producción o vía `ng serve`.
    - Consume el puerto `4200` y envía peticiones CORS habilitadas al backend.

 2. NODO SERVIDORE BACKEND (FastAPI / Uvicorn):
    - Corre sobre Python 3.10+ en el puerto `8000`.
    - Expone OpenAPI / Swagger en `http://localhost:8000/docs`.
    - Contiene los endpoints `/api/v1/adapt-content` y `/api/v1/parse-pdf`.

 3. SERVICIO DE VECTOR STORE EN MEMORIA (FAISS + BM25):
    - Genera embeddings densos con `sentence-transformers/all-MiniLM-L6-v2`.
    - Ejecuta búsquedas semánticas y léxicas cruzadas con re-ranking Cross-Encoder.

 4. SERVICIO EXTERNO IA GENERATIVA (Google Gemini 1.5):
    - Autenticado mediante variable de entorno `GEMINI_API_KEY` en el archivo `.env`.
    - Recibe el contexto recuperado y fuerza salidas estructuradas en Pydantic.

 5. ALMACENAMIENTO CLOUD (OCI Object Storage Always Free):
    - Conectado a través del SDK `oci`.
    - Almacena archivos originales bajo la carpeta `documentos/` y respuestas en `resultados/`.
    - En caso de entornos offline, cuenta con un fallback transparente de simulación de almacenamiento en disco local.
```

---

## 3. Re-implementación Avanzada de la Arquitectura RAG

Para garantizar la transformación didáctica de textos complejos (artículos científicos, tesis, manuales de software, monografías) sin pérdida de precisión ni alucinaciones, **NuevaMente** combina 4 arquitecturas de vanguardia:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PIPELINE INTEGRADO RAG DE NUEVAMENTE                   │
└─────────────────────────────────────────────────────────────────────────────┘

 [Documento Técnico / Paper / Manual]
                │
                ▼
 ┌───────────────────────────────────────────────────────────┐
 │ 1. PROCESAMIENTO JERÁRQUICO MAP-REDUCE                    │
 │    - Map: Extracción sintáctica por secciones (AST)      │
 │    - Reduce: Condensación y deduplicación de hallazgos     │
 └────────────────────────────┬──────────────────────────────┘
                              ▼
 ┌───────────────────────────────────────────────────────────┐
 │ 2. INDEXACIÓN DUAL Y MODELO DE DOMINIO                    │
 │    - Grafo RAG (DAG de conceptos y prerrequisitos)        │
 │    - Base de datos vectorial híbrida (Dense + BM25)       │
 └────────────────────────────┬──────────────────────────────┘
                              ▼
 ┌───────────────────────────────────────────────────────────┐
 │ 3. RECUPERACIÓN DIRIGIDA Y RE-RANKING                    │
 │    - Recorrido topológico en el grafo                    │
 │    - Búsqueda léxica puntual + Cross-Encoder Re-ranker     │
 └────────────────────────────┬──────────────────────────────┘
                              ▼
 ┌───────────────────────────────────────────────────────────┐
 │ 4. GENERACIÓN ADAPTATIVA Y AUDITORÍA DE FIDELIDAD         │
 │    - Inyección de variables: Perfil + Formato + Sector     │
 │    - Auditoría de Fact-checking y anclaje en fuentes (98%)│
 └───────────────────────────────────────────────────────────┘
```

---

### 3.1 Modelo de Dominio (Domain Model)
* **Propósito:** Adaptar el vocabulario técnico de dominios cerrados (Medicina, Biotecnología, Arquitectura de Software, Cloud Computing, Finanzas).
* **Funcionamiento:** Mantiene la nomenclatura exacta de código, fórmulas en LaTeX y parámetros numéricos sin simplificarlos excesivamente cuando el perfil del usuario es técnico o avanzado.

---

### 3.2 Modelo Map-Reduce (Procesamiento Jerárquico de Documentos Largos)
* **Fase Map:** Módulos paralelos procesan individualmente secciones críticas del documento (Introducción, Metodología, Resultados, Conclusiones), extrayendo afirmaciones clave y tablas en estructuras JSON independientes.
* **Fase Reduce:** Consolida los hallazgos eliminando redundancias interdocumentales y estructurando un resumen conceptual sintético para alimentar el Vector Store.

---

### 3.3 Arquitectura Graph RAG (Grafo de Conocimiento y DAG)
* **Capa Semántico-Topológica:** Mapea las dependencias conceptuales mediante un Grafo Acíclico Dirigido (DAG).
* **Alineamiento Constructivo:** Verifica que cada concepto avanzado tenga nodos de prerrequisitos previos en el temario, evitando brechas cognitivas y dependencias circulares.

---

### 3.4 RAG Híbrido con Re-ranking Especializado
* **Búsqueda Densa (Dense Vectors):** Emplea vectores de embeddings para capturar la intención semántica general.
* **Búsqueda Dispersa (Sparse / BM25):** Recupera nombres exactos de funciones, acrónimos, códigos de error y fórmulas.
* **Re-ranking con Cross-Encoder:** Un modelo posterior (*Cross-Encoder*) evalúa simultáneamente la consulta del usuario y el pasaje recuperado, filtrando falsos positivos semánticos antes de pasar el contexto final a Google Gemini.
