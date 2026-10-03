# MANUAL TÉCNICO: SISTEMA NUEVAMENTE
*Documento Confidencial - Uso Interno Exclusivo*
*Versión 1.0 - Octubre 2026*
*Autor: Equipo G10 LATAM*

---
## Índice
1. [Introducción](#guía-definitiva-de-rag-y-conceptos-del-backend)
2. [¿Qué es RAG?](#1-qué-es-rag-retrieval-augmented-generation)
3. [Ingesta y Chunking](#2-ingesta-y-chunking-fragmentación)
4. [Embeddings y Vector Store](#3-embeddings-y-vector-store)
5. [Generación y Casos de Uso](#4-rag-tradicional-vs-generación-de-resúmenesflashcards)
6. [Anexos: Métricas](#5-anexos-métricas-de-rendimiento)

---
*Página 1 de 6 - Confidencial*

# Guía Definitiva de RAG y Conceptos del Backend

Este documento es una guía técnica que explica cómo funciona el pipeline de ingesta, embeddings y RAG dentro del sistema NuevaMente. Su propósito no es solo ser informativo, sino también servir como un archivo de prueba ideal para `test_ingestion_sample.py` debido a su estructura con encabezados y contenido técnico.

## 1. ¿Qué es RAG (Retrieval-Augmented Generation)?

RAG es una técnica que mejora las respuestas de un modelo de lenguaje (LLM) al proporcionarle contexto externo y actualizado antes de que genere su respuesta. 

En lugar de depender exclusivamente del conocimiento con el que el modelo fue entrenado (que puede estar desactualizado o no tener información privada de la empresa), RAG busca en una base de datos de documentos relevantes y le dice al LLM: *"Basándote únicamente en este texto que encontré, responde a la pregunta del usuario"*.

*Advertencia de Seguridad: Nunca exponga claves de API ni contraseñas en los prompts de los agentes.*

### Diferencia entre RAG y Fine-tuning
Una de las preguntas más comunes es: ¿RAG permite que el LLM responda sin tener que entrenarlo? 
**La respuesta es SÍ.**
*   **Fine-tuning (Entrenamiento):** Es costoso, requiere miles de ejemplos y el modelo aún puede alucinar datos exactos. Es útil para cambiar el *estilo* o *tono* del modelo.
*   **RAG:** No entrena al modelo. Simplemente inyecta información fresca en el *Prompt*. Es más barato, más rápido de actualizar (solo subes un nuevo documento) y evita alucinaciones porque obligas al modelo a ceñirse al contexto proporcionado.

---
*Página 2 de 6 - Confidencial*

## 2. Ingesta y Chunking (Fragmentación)

Los modelos de lenguaje tienen un límite de cuánto texto pueden leer a la vez (ventana de contexto). Por eso, no podemos enviar un libro de 500 páginas en cada pregunta. Aquí entra el **Chunking**.

### ¿Qué son los Chunks?
Son fragmentos de texto más pequeños extraídos del documento original. 

### Enfoque Jerárquico (Parent-Child)
En nuestro backend, usamos una técnica avanzada llamada *Parent-Child Chunking*:
1.  **Parent Chunks:** Son fragmentos grandes que corresponden a secciones lógicas del documento (por ejemplo, todo el contenido debajo de un subtítulo). Mantienen el contexto completo.
2.  **Child Chunks:** Son fragmentos más pequeños derivados de los Parent Chunks. 

¿Por qué hacerlo así? Los *Child Chunks* son excelentes para buscar coincidencias exactas y semánticas precisas. Pero cuando se los enviamos al LLM, le pasamos el *Parent Chunk* asociado. Así, buscamos con precisión milimétrica, pero el LLM lee el contexto general para dar una mejor respuesta.

---
*Página 3 de 6 - Confidencial*

## 3. Embeddings y Vector Store

### ¿Qué son los Embeddings?
Las computadoras no entienden las palabras como texto, entienden números. Un **Embedding** es la conversión de un texto (un chunk) en una larga lista de números (un vector de cientos o miles de dimensiones).
Esta lista de números captura el *significado semántico* del texto. Frases con significados similares ("gato" y "felino") tendrán vectores numéricos que están cerca matemáticamente.

### ¿Qué es el Vector Store (FAISS)?
FAISS (Facebook AI Similarity Search) es nuestra base de datos vectorial local. Su trabajo es almacenar todos esos vectores generados.
Cuando el usuario hace una pregunta, la pregunta también se convierte en un vector (Embedding). Luego, FAISS calcula la distancia matemática entre el vector de la pregunta y todos los vectores de la base de datos para encontrar los *Child Chunks* más relevantes en milisegundos.

*Nota Técnica: FAISS debe reiniciarse si se cambia el modelo de Embedding (ej. pasar de Gemini a Jina).*

---
*Página 4 de 6 - Confidencial*

## 4. RAG Tradicional vs. Generación de Resúmenes/Flashcards

Existe una confusión común sobre si RAG se usa o no para generar resúmenes o flashcards. Aquí está la aclaración arquitectónica:

### Casos de uso de Búsqueda Semántica (RAG estricto)
Se usa cuando el usuario pregunta algo específico, o quiere flashcards de un **tema en particular**.
*   *Ejemplo:* "Genera flashcards sobre el concepto de Embeddings".
*   *Flujo:* Pregunta -> Embedding -> FAISS (encuentra chunks sobre Embeddings) -> LLM genera flashcards basadas solo en esos chunks.

### Casos de uso de Transformación Total
Se usa cuando se quiere un resumen o flashcards de **todo el documento**.
*   *Flujo:* No tiene sentido buscar por similitud si quieres resumir *todo*. En este caso, **saltamos el paso de FAISS**. Extraemos todos los *Parent Chunks* almacenados en la metadata y se los pasamos directamente al LLM (Agente) para que lea todo y genere el material.

---
*Página 5 de 6 - Confidencial*

### La Capa de Agentes (Agent Orchestrator)
En nuestra arquitectura, el archivo `agent_orchestrator.py` es el cerebro que conecta el RAG con la generación final. Este orquestador recibe los chunks (ya sea por búsqueda de FAISS o todos los del documento) y arma el *Mega-Prompt* inyectando el contexto y pidiendo el formato final (JSON para Quizzes, Flashcards, Tutoriales o TLDR) que será consumido por el Frontend.

---
*Página 6 de 6 - Confidencial*

## 5. Anexos: Métricas de Rendimiento

A continuación, se presentan los tiempos de respuesta esperados de la arquitectura bajo carga normal para validar el rendimiento:

| Componente | Proveedor | Latencia Media (ms) | Tokens por Minuto | Límite de Peticiones |
| :--- | :--- | :--- | :--- | :--- |
| Embedding API | Gemini 1.5 | 350 | 4.000.000 | 1500 RPM |
| Fallback Embed | Jina AI | 420 | 1.000.000 | 500 RPM |
| Vector Store | FAISS (Local)| 15 | N/A | Sin límite |
| Reranker | Cohere V3 | 280 | N/A | 1000 RPM |
| Generación | Groq Llama 3 | 850 | 14.400 | 30 RPM |

*Nota final al administrador: Monitoree el límite de Groq, es el cuello de botella en los agentes.*
*Documento generado automáticamente por el pipeline. No imprimir.*
