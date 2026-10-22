# Anclaje de fuentes (explicación)

> `docs/01-Arquitectura/` · [Volver al README](../../README.md)

**NuevaMente** genera contenido educativo con un modelo de lenguaje (LLM). Un
LLM puede escribir frases muy convincentes que **no** están en el documento
original. Eso es exactamente lo que un material de formación no puede permitirse.
El **anclaje** es el mecanismo que comprueba que cada idea generada esté
respaldada por un fragmento real del documento que subiste.

Este documento explica el *qué* y el *por qué*, sin código. Si necesitas el
detalle de implementación, consulta
[Anclaje técnico](../04-Documentacion/backend/quality/Anclaje_Tecnico.md).

---

## 1. El problema en una frase

> El modelo redacta; el documento manda.

Cuando pides, por ejemplo, cinco flashcards, el modelo no se limita a copiar
texto: parafrasea, resume y ordena. En ese proceso puede añadir un dato que
suena correcto pero que no aparece en la fuente. El anclaje detecta esas
invenciones (o "alucinaciones") antes de mostrarte el resultado.

---

## 2. Cómo funciona, paso a paso

```text
Documento original
      │
      ▼
Fragmentos (chunks) ya indexados
      │
      ▼
El modelo escribe los elementos
(flashcards, preguntas, secciones)
      │
      ▼
Cada elemento debe citar de dónde sale
      │
      ▼
   ┌──────────────────────────────┐
   │  Dos revisores independientes │
   └──────────────────────────────┘
      │                        │
      ▼                        ▼
1. Comprobación        2. Revisión por IA
   automática             (un segundo modelo
   (compara el texto       actúa como auditor)
   con el fragmento)
      │                        │
      └───────────┬────────────┘
                  ▼
      Solo cuenta como "verificado"
      si pasan LAS DOS
                  │
                  ▼
      Sello de Confianza + lista de fuentes
```

### 2.1 Cada elemento cita su origen

Antes de validar nada, el modelo debe indicar **de qué fragmento** sacó cada
idea. Esa cita incluye el identificador del fragmento, un extracto del texto y,
cuando existe, la página y la ruta de la sección (por ejemplo
`Manual BX-200 > Capítulo 1 > 1.1 Descripción general`).

### 2.2 Dos revisores, no uno

- **Comprobación automática:** compara la cita con el texto real del fragmento.
  Sirve para detectar citas inventadas, cifras que no aparecen y negaciones
  ("no se debe…") que la fuente no dice.
- **Revisión por IA:** un segundo modelo lee el elemento y las fuentes citadas
  y decide si la afirmación está respaldada, además de valorar su claridad
  pedagógica.

Usar dos revisores es intencional: el automático es rápido pero rígido; el de
IA entiende paráfrasis pero podría ser demasiado indulgente. Solo si **ambos**
dan el visto bueno, el elemento se considera verificado.

### 2.3 Si algo falla, se intenta arreglar

Cuando un elemento no queda verificado o se detecta con poca claridad, el
sistema no lo publica tal cual: envía ese elemento concreto a una **reparación**
(se reescribe usando las fuentes) y lo vuelve a someter a los dos revisores.
Hay un límite de intentos para no entrar en un bucle infinito.

Si tras la reparación sigue sin respaldo, el elemento se descarta.

---

## 3. Qué significa el Sello de Confianza

En la interfaz verás un indicador circular con un porcentaje de **fidelidad**.
No es una nota de estilo: es la proporción de elementos que quedaron
verificados sobre el total publicado.

| Porcentaje | Etiqueta | Qué quiere decir |
| :--- | :--- | :--- |
| 90 % o más | **Excelente** | Casi todo está respaldado por el documento. |
| 75 % – 89 % | **Muy bueno** | La mayoría está respaldado; revisa los pocos puntos flojos. |
| 60 % – 74 % | **Revisa algunos puntos** | Hay elementos que conviene contrastar con la fuente. |
| Menos de 60 % | **Verifica con la fuente** | El contenido necesita revisión humana antes de usarse. |

> Un porcentaje bajo **no** significa que el sistema esté roto: significa que el
> documento no cubría bien lo que se pidió, o que el formato elegido exige
> información que la fuente no tiene.

Junto al sello aparecen:

- cuántos elementos se verificaron sobre el total;
- el nivel de **claridad pedagógica**;
- las **notas de revisión** (qué se descartó o reparó);
- la lista de **fuentes** de cada elemento, con una marca de "verificado" por
  cita.

---

## 4. Qué hacer si el anclaje sale bajo

1. **Comprueba la cobertura del documento.** Si pediste 20 preguntas y el
   documento solo tiene dos páginas, el modelo no tiene de dónde sacarlas.
2. **Baja la cantidad solicitada** o elige un formato más adecuado.
3. **Revisa las fuentes marcadas como no verificadas** y contrasta esos puntos
   concretos con el documento original.
4. **Vuelve a generar** si el documento estaba mal extraído (por ejemplo, un PDF
   escaneado sin capa de texto).

---

## 5. Qué no hace el anclaje

- No corrige errores que **ya estaban** en el documento original: si la fuente
  dice algo incorrecto, el contenido adaptado lo repetirá (y estará "anclado").
- No sustituye una revisión humana en materiales críticos.
- No garantiza calidad pedagógica: eso lo evalúa la claridad, que es un criterio
  distinto.

---

<div align="right">

[Volver al README](../../README.md)

</div>
