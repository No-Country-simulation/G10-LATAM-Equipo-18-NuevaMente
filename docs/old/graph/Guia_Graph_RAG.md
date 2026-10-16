# Guía de Graph RAG — NuevaMente

## ¿Qué es Graph RAG?
Graph RAG (Retrieval-Augmented Generation basado en Grafos) es una técnica avanzada que extrae conceptos clave y sus relaciones (prerrequisitos, asociaciones) a partir de los documentos, construyendo un **Knowledge Graph (Grafo de Conocimiento)** estructurado. Esto permite que el LLM no solo tenga fragmentos de texto inconexos, sino una vista jerárquica de qué conceptos dependen de cuáles.

## Arquitectura y Flujo de Extracción

El servicio `GraphRAGService` implementa una cascada de resiliencia (Chain of Responsibility) para asegurar que el grafo siempre se genere:

1. **Plan A (Gemini LLM):** El texto se envía a Google Gemini. Se le instruye extraer los conceptos y relaciones más importantes en formato `JSON`. Esta es la forma más potente y precisa de extraer relaciones semánticas complejas.
2. **Plan B (Jina AI Fallback):** Si Gemini se queda sin tokens o cuota, el sistema activa Jina AI. 
   - Extrae palabras clave (en mayúsculas/títulos).
   - Corta el texto y las palabras candidatas a la **mitad (50%)** del tamaño original para ahorrar costos dinámicamente dependiendo de si el texto es largo o muy corto.
   - Usa los **Embeddings** de Jina y la **Similitud del Coseno** para encontrar matemáticamente qué palabras son más relevantes al texto completo.
3. **Plan C (Reglas Locales):** Si falla Jina por falta de red, se usan heurísticas de Python clásicas como último recurso para evitar que la aplicación colapse (Resiliencia).

## Clean Code en el Graph RAG
Actualmente la lógica reside en el mismo servicio (`GraphRAGService`). Aunque es altamente funcional para esta etapa del proyecto, una evolución natural bajo principios SOLID sería aislar cada "Plan" en su propia clase utilizando un patrón *Strategy* o una *Cadena de Responsabilidad*, de manera que agregar un nuevo proveedor en el futuro no modifique el servicio principal.

## ¿Por qué esto hace que NuevaMente sea un mejor proyecto?
Para el Hackathon (y para cualquier entorno productivo), implementar Graph RAG de esta manera aporta un valor técnico enorme:
1. **Resiliencia Extrema:** La aplicación no colapsa si falla la API principal. Siempre hay un Plan B y Plan C.
2. **Eficiencia en Costos:** Al truncar matemáticamente los textos y limitar los conceptos antes de enviarlos a Jina AI, se protege la cuota gratuita (tokens), asegurando que el sistema pueda operar por más tiempo sin costos.
3. **Calidad de Contexto:** El LLM final recibirá un "mapa mental" de cómo se relacionan los temas en lugar de simples párrafos sueltos. Esto reduce las alucinaciones y permite generar planes de estudio mucho más lógicos y adaptados al estudiante.

## ¿Cómo ejecutar el proyecto usando `uv`?
`uv` es un gestor de paquetes y dependencias en Python extremadamente rápido (escrito en Rust). 

Para instalar las dependencias necesarias y correr el servicio que usa este Grafo:

```bash
# 1. Asegúrate de estar en el directorio del backend
cd backend

# 2. Sincroniza e instala las dependencias usando uv (lee el pyproject.toml / uv.lock)
uv sync

# 3. Activa el entorno virtual creado por uv
source .venv/bin/activate

# 4. Inicia el servidor de FastAPI
uv run uvicorn main:app --reload
```
