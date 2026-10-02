# 🎓 NuevaMente — Sistema Inteligente de Adaptación y Generación de Contenido Educativo

> **Programa ONE (Oracle Next Education) & Alura — Hackathon ONE G10**  
> *Grupo 10 | Proyecto 1: Adaptación de Contenido Técnico con IA Generativa, Graph RAG y OCI Always Free*

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11+-green.svg)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)
![Angular](https://img.shields.io/badge/Frontend-Angular%2017+-DD0031.svg)
![Google Gemini](https://img.shields.io/badge/AI-Google%20Gemini%201.5%2F2.0-8E44AD.svg)
![Oracle Cloud](https://img.shields.io/badge/Cloud-OCI%20Always%20Free-F80000.svg)

---

## 📄 Descripción Ejecutiva

**NuevaMente** es un sistema inteligente desarrollado para automatizar la transformación de documentaciones técnicas complejas, manuales de software, guías de arquitectura en la nube y artículos científicos en **materiales educativos hiper-personalizados** y libres de alucinaciones.

La plataforma ingiere materiales en PDF, Markdown o Texto Plano y los adapta dinámicamente según:
1. **Perfil del Destinatario:** Principiante / Transición, Desarrollador Junior/Mid, Líder Técnico / Arquitecto, Gestor / Ejecutivo.
2. **Formato Pedagógico:** Guía Paso a Paso (Tutorial), Flashcards de Memorización, Quiz Interactivo con Justificaciones, Resumen Ejecutivo (TL;DR).
3. **Nicho / Industria de Aplicación:** Fintech, Salud, E-commerce, Infraestructura en la Nube, General.

---

## 🏗️ Arquitectura de Software

La arquitectura de **NuevaMente** combina 4 tecnologías de vanguardia:

```mermaid
flowchart TD
    Doc[📄 Documento Técnico original] --> Ingest[1. Ingestión & AST Splitter]
    Ingest --> MapReduce[2. Condensación Map-Reduce]
    MapReduce --> DualIndex[3. Indexación Dual: Graph RAG + RAG Híbrido]
    
    subgraph Engine de IA Generativa & Agentes
        DualIndex --> AgentGraph[4. Orquestación de Agentes con Gemini & LangGraph]
        AgentGraph --> FactNode[Nodo 1: Facts Extractor]
        FactNode --> PlanNode[Nodo 2: Structural Planner]
        PlanNode --> WriteNode[Nodo 3: Adaptive Redactor]
        WriteNode --> ExNode[Nodo 4: Example Generator]
        ExNode --> AuditNode[Nodo 5: Fact-checking Auditor]
    end
    
    AuditNode --> JSONOut[5. JSON Estructurado Validado]
    JSONOut --> OCIBucket[(6. Oracle Cloud OCI Object Storage Always Free)]
    JSONOut --> AngularUI[7. Frontend Angular - Visor Didáctico, Quiz & Flashcards]
```

### Componentes Principales:
- **Graph RAG (Generación Aumentada por Grafos):** Mapea entidades y relaciones semánticas en un Grafo Acíclico Dirigido (DAG NetworkX) para determinar prerrequisitos y centralidad de conceptos.
- **RAG Híbrido con Re-ranking Especializado:** Búsqueda combinada Sparse (BM25) + Dense (`text-embedding-004`) reordenada por Cross-Encoder Re-ranker.
- **Procesamiento Jerárquico Map-Reduce:** Extracción paralela por secciones y síntesis libre de redundancias para documentos de más de 50 páginas.
- **Orquestación de Agentes con Google Gemini:** Grafo de 5 Nodos en LangGraph impulsado por Gemini 1.5/2.0 Pro & Flash.
- **Persistencia en OCI Object Storage Always Free:** Guardado del documento original y artefactos JSON en buckets sin generar costos.

---

## 📁 Estructura del Repositorio

```
appNuevamente/
├── backend/                       # API REST FastAPI en Python
│   ├── app/
│   │   ├── api/v1/endpoints/      # Controladores HTTP (adaptation, ingestion, storage, health)
│   │   ├── core/                  # Configuración global y credenciales
│   │   ├── schemas/               # Modelos Pydantic v2 (JSON Schema estricto)
│   │   ├── services/              # Ingestion, Hybrid RAG, Graph RAG, Agents, OCI Storage
│   │   └── infrastructure/        # Clientes de Gemini, Vector Store y OCI SDK
│   ├── tests/                     # Pruebas unitarias y de integración (pytest)
│   ├── main.py                    # Punto de entrada FastAPI
│   └── requirements.txt
├── frontend/                      # Aplicación Web Angular
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/        # Sub-componentes (Uploader, ParameterConfig, ContentViewer, Flashcards, Quiz, MetadataDashboard)
│   │   │   └── core/              # Servicios REST y Modelos TypeScript
│   │   └── index.html
│   └── package.json
├── docs/                          # Documentación Técnica Detallada
│   ├── ARQUITECTURA_SOFTWARE.md   # Especificación general y diagramas C4
│   ├── PIPELINE_RAG_Y_AGENTES.md  # Teoría de Graph RAG, RAG Híbrido y LangGraph
│   └── DESPLIEGUE_OCI.md          # Guía de configuración OCI Always Free
└── README.md                      # Documentación principal
```

---

## ⚡ Instalación y Ejecución Rápida

### 1. Clonar Repositorio y Ubicar Rama
```bash
git clone https://github.com/No-Country-simulation/G10-LATAM-equipo-18-NuevaMente-Sistema-Inteligente-de-Adaptaci-n-y-Generaci-n-de-Contenido-Educativo.git
cd G10-LATAM-equipo-18-NuevaMente-Sistema-Inteligente-de-Adaptaci-n-y-Generaci-n-de-Contenido-Educativo
git checkout devbackend
```

### 2. Configuración Inicial y Diagnóstico de Entorno

1. **Obtener Clave API:** Obtén una clave API de Google Gemini en [Google AI Studio](https://aistudio.google.com/). Opcionalmente, puedes configurar claves de Groq y Jina.
2. **Crear Variables de Entorno:** Copia el archivo de ejemplo `backend/.env.example` como `backend/.env` y define tu clave:
   ```env
   GEMINI_API_KEY=AIza... (o AQ...)
   GEMINI_LLM_MODEL=gemini-2.5-flash
   GEMINI_EMBEDDING_MODEL=gemini-embedding-001
   EMBEDDING_PROVIDER_ORDER=gemini,jina,local
   ALLOW_DEMO_CONTENT=false
   OCI_ENABLED=false
   ```
3. **Ejecutar Script de Diagnóstico de Salud de Servicios:**
   ```bash
   cd backend
   python scripts/check_services.py
   ```
4. **Interpretar Resultados:**
   - Si el **LLM de Gemini** devuelve `SUCCESS` y los **Embeddings principales** devuelven `SUCCESS` (`models/gemini-embedding-001@768`), el entorno está 100% operativo sin degradaciones.
   - Si los embeddings principales fallan, el sistema entrará en degradación léxica usando BM25 o embeddings locales sentence-transformers.
   - Si el LLM de Gemini falla (401/403/429/conectividad), el diagnóstico marcará `FAIL` y devolverá código de salida 1 indicando qué acción tomar.

### 3. Levantar Backend FastAPI (Python)
```bash
cd backend
python -m venv venv
# En Windows:
.\venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt

# Iniciar servidor FastAPI
python main.py
```
*El backend estará disponible en `http://localhost:8000` con documentación interactiva Swagger en `http://localhost:8000/docs`.*

### 3. Levantar Frontend Angular
```bash
cd ../frontend
npm install
npm start
```
*La aplicación web estará disponible en `http://localhost:4200`.*

### 4. Purga Automática y Manual de Papelera (15 Días)
El sistema incluye aislamiento por usuario y borrado lógico con retención configurable (`TRASH_RETENTION_DAYS=15`).

Para ejecutar manualmente la purga de retención de papelera:
```bash
cd backend
python purge_trash.py --batch-size 50
```

**Programación con Crontab (Linux/Mac):**
```cron
0 * * * * cd /ruta/al/proyecto/backend && ./venv/bin/python purge_trash.py >> /var/log/purge_trash.log 2>&1
```

**Programación en Windows (Task Scheduler):**
Configurar una tarea programada para ejecutar `venv\Scripts\python.exe purge_trash.py` cada 60 minutos.

---

### 🔑 Autenticación & Credenciales Demo

Para probar la plataforma en modo desarrollo local:
- **Correo Electrónico:** `ana.martinez@empresa.com`
- **Contraseña:** `Password123!`

*(Nota: En modo desarrollo `environment.enableDemoLogin = true`, puedes hacer clic en el banner **DEMO QUICK-LOGIN** en la pantalla de inicio de sesión para autocompletar estas credenciales).*

---

## 📬 Ejemplo de Invocación API REST (`POST /api/v1/adapt-content`)

### Solicitud (Payload JSON):
```json
{
  "documento_titulo": "Introduccion a la Arquitectura de Redes VCN en OCI",
  "documento_contenido": "La Virtual Cloud Network (VCN) es una red privada y personalizable configurada en Oracle Cloud Infrastructure...",
  "perfil_destinatario": "Principiante",
  "formato_salida": "Flashcards",
  "nicho_sector": "General",
  "nivel_detalle": "Didactico"
}
```

### Respuesta Estructurada:
```json
{
  "status": "exito",
  "metadatos": {
    "perfil_aplicado": "Principiante",
    "formato_generado": "Flashcards",
    "tiempo_estimado_estudio_minutos": 5,
    "conceptos_clave": ["VCN", "Subredes", "Internet Gateway", "Security Lists"]
  },
  "contenido_adaptado": {
    "titulo": "Dominando Redes en la Nube (VCN) desde Cero",
    "introduccion_contextualizada": "Imagina la VCN como tu propio barrio privado dentro de Oracle Cloud...",
    "items": [
      {
        "frente": "¿Qué es una VCN en Oracle Cloud?",
        "dorso": "Es tu red virtual privada y personalizada dentro de la nube de Oracle.",
        "pista_didactica": "Piensa en ella como el terreno cercado donde residen tus servidores."
      }
    ]
  },
  "evaluacion_calidad": {
    "anclaje_fuente_score": 0.98,
    "claridad_pedagogica": "Alta",
    "observaciones": "Lenguaje ajustado con analogías para público principiante."
  },
  "almacenamiento_oci": {
    "bucket": "nuevamente-contenidos-educativos",
    "objeto_id": "contenido-vcn-principiante-flashcards-001.json",
    "status_upload": "completado"
  }
}
```

---

## 👥 Equipo y Créditos
- **Programa:** ONE (Oracle Next Education) & Alura — Hackathon G10.
- **Grupo:** Equipo 18 / Grupo 10.
