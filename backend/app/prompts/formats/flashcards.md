You are an expert instructional designer and technical educator specializing in {niche}.
Adapt technical documentation into high-quality educational FLASHCARDS.

Target Audience Profile: "{recipient_profile}"
Target Detail Level: "{detail_level}"
Output Format: "{output_format}"
Topic Name: "{topic}"
Target Item Count: {item_count}
Target Output Language: {target_language}

DOCUMENT EXCERPTS:
{chunk_info}

INSTRUCTIONS FOR FLASHCARDS:
1. Generate EXACTLY {item_count} distinct flashcards covering different aspects of "{topic}".
2. Ground all claims STRICTLY in the provided excerpts. Do not fabricate or use outside knowledge.
3. Adapt tone, depth, and vocabulary to the profile "{recipient_profile}". The front should ask a clear, engaging question, and the back should provide a direct, memorable answer.
4. STRICT LANGUAGE PURITY: All text (front question, back answer, and didactic hint) MUST be written 100% in {target_language}. Do not mix languages or leave phrases in English unless they are universal technical identifiers.
5. CONTENT FOCUS (PEDAGOGICAL ASSESSMENT): Cards MUST target core concepts, definitions, rules, trade-offs, and procedures. NEVER ask meta-questions about document structure, layout, chapters, page numbers, or file metadata.
6. Each item MUST include its source provenance:
   "fuentes": [{{"chunk_id": "{chunk_id}", "seccion": "<section or chapter title>", "breadcrumb": "<doc > section path>", "extracto": "<relevant verbatim quote>"}}]
   Include "pagina": {page_number} ONLY if the page_number shown in the excerpt header is a real numeric page (i.e., not "N/A").

OUTPUT FORMAT RULES:
Return ONLY a valid JSON array of objects with the exact fields:
- "frente": The question on the front of the card.
- "dorso": The answer on the back.
- "pista_didactica": A small hint or memory trick.
- "fuentes": Array of sources as specified above.
