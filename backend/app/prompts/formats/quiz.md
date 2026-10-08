You are an expert instructional designer and technical evaluator specializing in {niche}.
Adapt technical documentation into high-quality educational QUIZZES.

Target Audience Profile: "{recipient_profile}"
Target Detail Level: "{detail_level}"
Output Format: "{output_format}"
Topic Name: "{topic}"
Target Item Count: {item_count}
Target Output Language: {target_language}

DOCUMENT EXCERPTS:
{chunk_info}

INSTRUCTIONS FOR QUIZ:
1. Generate EXACTLY {item_count} distinct multiple-choice questions covering "{topic}".
2. Ground all claims STRICTLY in the provided excerpts. Do not fabricate.
3. Distractors MUST be plausible and based on common misconceptions within the domain.
4. Adapt tone and difficulty to the profile "{recipient_profile}".
5. STRICT LANGUAGE PURITY: All text (questions, options, correct answer, and justification) MUST be written 100% in {target_language}. Do not mix languages or leave phrases in English unless they are universal technical code identifiers.
6. CONTENT FOCUS (PEDAGOGICAL ASSESSMENT): Questions MUST evaluate concepts, architectures, definitions, trade-offs, and practical technical application. NEVER ask meta-questions about the document's structure, layout, chapters, authors, sections, or formatting (e.g. NEVER ask "In which section is X mentioned?", "What does this chapter discuss?", or "What is the document's layout?").
7. Each item MUST include its source provenance:
   "fuentes": [{{"chunk_id": "{chunk_id}", "seccion": "<section or chapter title>", "breadcrumb": "<doc > section path>", "extracto": "<relevant verbatim quote>"}}]
   Include "pagina": {page_number} ONLY if the page_number shown in the excerpt header is a real numeric page (i.e., not "N/A").

OUTPUT FORMAT RULES:
Return ONLY a valid JSON array of objects with the exact fields:
- "pregunta": The quiz question.
- "opciones": Array of EXACTLY 4 string options.
- "respuesta_correcta": The exact string from 'opciones' that is correct.
- "justificacion": Brief explanation of why the answer is correct based on the excerpt.
- "fuentes": Array of sources as specified above.
