# 🚀 Justificación de Arquitectura IA y Memoria Técnica
**Proyecto:** NuevaMente — Sistema Inteligente de Adaptación Educativa
**Hackathon:** ONE G10 (Oracle Next Education & Alura)

---

## 1. Resumen Ejecutivo de la Evolución
El proyecto pasó de tener una canalización monolítica dependiente de un solo LLM (Gemini) a convertirse en un **Ecosistema Multi-Agente Resiliente con Arquitectura Limpia (Clean Architecture)**. Hemos integrado visión artificial (Multimodal), parseo semántico de PDFs y un enrutador inteligente de tareas.

Esto transforma a NuevaMente en una herramienta verdaderamente *Enterprise*, optimizando **costos, velocidad, precisión y privacidad**.

---

## 2. El Ecosistema Multi-Agente: ¿Por qué elegimos estos Modelos?

El principio de diseño arquitectónico es: *"Usar la herramienta adecuada para el trabajo adecuado"*. Obligar a un modelo gigante a hacer tareas sencillas es caro y lento; obligar a un modelo pequeño a investigar es impreciso.

| Agente / Modelo | Propósito Principal en el Sistema | Justificación de la Elección (El "Por qué") |
| :--- | :--- | :--- |
| **Gemini 1.5 Pro/Flash** | *Deep Research, Síntesis y Tareas Pesadas* | Su inmensa ventana de contexto (hasta 2M de tokens) lo hace imbatible para leer monografías enteras, cruzar datos y realizar "Deep Reasoning" sin olvidar información. |
| **Groq (Llama-3 70B)** | *Generación Ultrarrápida y Formateo* | Groq usa procesadores LPU (Language Processing Units) que generan cientos de tokens por segundo. Se usa exclusivamente para extraer Flashcards y Quizzes porque reduce la latencia a milisegundos, mejorando drásticamente la Experiencia de Usuario (UX). |
| **Ollama (Llama-3 Local)** | *Fallback y Privacidad Absoluta* | Sirve como la red de seguridad del sistema. Si los servidores en la nube fallan (Error 503) o el usuario sube un documento con datos confidenciales, el tráfico se enruta a la máquina local, garantizando privacidad y 0% de tiempo de inactividad. |
| **Qwen-VL / Gemini Vision** | *Análisis Multimodal de Diagramas* | La educación técnica depende de gráficos (Ej. topologías de red en OCI o diagramas Entidad-Relación). Estos modelos permiten al sistema "ver" imágenes y transformarlas en explicaciones y tarjetas de estudio (Anki). |
| **Cohere (Rerank-V3)** | *Cross-Encoder para Búsqueda Híbrida* | Resolver el problema *"Lost in the middle"*. Cohere es el estado del arte en modelos multilingües, garantizando que los fragmentos de texto más relevantes en español suban al Top 3 antes de ser leídos por la IA. |
| **Jina AI (Embeddings)** | *Vectorización Semántica* | Ofrece embeddings de altísima calidad (8192 tokens de contexto) a una fracción del costo, ideal para indexar bases de conocimientos completas. |

---

## 3. Innovaciones Técnicas Implementadas

### A. Clean Architecture (Capa de Infraestructura)
Hemos abstraído todas las conexiones a APIs externas (`gemini_client.py`, `groq_client.py`, `jina_client.py`, `cohere_client.py`) en una capa de **Infraestructura**. 
* **Beneficio:** Si mañana sale un modelo mejor (ej. GPT-5), la lógica pedagógica del Orquestador y del RAG no se toca. Solo se crea un nuevo cliente. Además, implementamos un patrón "Mock" que devuelve respuestas simuladas si falla la conexión, asegurando que el Frontend (Angular) jamás reciba un error fatal de validación (Pydantic).

### B. El "Policía de Tráfico" (Multi-Agent Router)
Se desarrolló la clase `MultiAgentRouter`, un sistema de heurística y regex que analiza la petición del usuario en tiempo real. 
* **Ejemplo:** Si el usuario pide un "Quiz", el Router detecta la necesidad de velocidad y asigna la tarea a **GROQ**. Si el usuario sube un PDF pesado y pide un "Análisis Profundo", asigna la tarea a **GEMINI**. 

### C. Parseo Inteligente de PDFs (Markdown RAG)
A diferencia de los RAGs tradicionales que extraen el PDF como un bloque de texto ininteligible, integramos `pymupdf4llm`.
* **Beneficio:** Convierte los PDFs directamente a formato Markdown. Preserva la estructura de las tablas, respeta los niveles de encabezados (H1, H2) y elimina pies de página repetidos. Esto evita que el LLM alucine al intentar leer tablas rotas.

### D. Endpoint Multimodal para Flashcards Visuales
Se creó una ruta especializada `/extract-diagram` que acepta imágenes.
* **Beneficio:** Rompe la barrera del "solo texto". Un estudiante puede tomarle una foto a un diagrama de arquitectura en la pizarra y el sistema automáticamente le generará tarjetas de estudio (Flashcards) explicando cada componente de la imagen.

---

## 4. ¿Por qué esto hace que el proyecto sea "El Mejor"?

Para los jueces del Hackathon, este sistema demuestra un nivel de **Ingeniería de Software Senior**:
1. **Resiliencia Extrema:** No importa si la API de Google se cae por alta demanda; el sistema enruta a Ollama o activa su Mock System y la aplicación sigue funcionando.
2. **Eficiencia en Costos (FinOps):** Usar la inferencia más pesada solo cuando es estrictamente necesario, y delegar tareas triviales a modelos más económicos o rápidos.
3. **Calidad de Contexto (Markdown + Reranking):** El LLM ya no lee "basura". Lee tablas perfectas gracias al nuevo parseador, y lee solo lo más relevante gracias a la búsqueda híbrida léxica/densa reordenada por Cohere.
4. **Escalabilidad:** El diseño de "Clean Architecture" significa que agregar un nuevo agente (como Cerebras o Claude) toma 5 minutos de código sin alterar la lógica de negocio.

Con estos pilares, **NuevaMente** no es solo una llamada a la API de OpenAI/Gemini; es un auténtico motor de razonamiento compuesto de múltiples cerebros trabajando en armonía.
