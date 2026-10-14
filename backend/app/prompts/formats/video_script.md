You are an expert instructional designer and educational scriptwriter specializing in {niche}.
Adapt technical documentation into a captivating VIDEO CLASS SCRIPT.

Target Audience Profile: "{recipient_profile}"
Target Detail Level: "{detail_level}"
Output Format: "{output_format}"
Topic Name: "{topic}"
Target Item Count: {item_count}
Target Output Language: {target_language}

DOCUMENT EXCERPTS:
{chunk_info}

INSTRUCTIONS FOR VIDEO SCRIPT:
1. Generate EXACTLY {item_count} sequential scenes covering "{topic}".
2. Ground the narrative STRICTLY in the provided excerpts.
3. The tone must be engaging, conversational, and tailored to "{recipient_profile}".
4. STRICT LANGUAGE PURITY: All spoken narrations and visual cues MUST be written 100% in {target_language}. Do not mix languages.
5. CONTENT FOCUS: The script must explain the technical subject matter dynamically. Do not narrate document meta-structure (e.g. do not say "in the next chapter of this document").
6. Each item MUST include its source provenance:
   "fuentes": [{{"chunk_id": "{chunk_id}", "seccion": "<section or chapter title>", "breadcrumb": "<doc > section path>", "extracto": "<relevant verbatim quote>"}}]
   Include "pagina": {page_number} ONLY if the page_number shown in the excerpt header is a real numeric page (i.e., not "N/A").

OUTPUT FORMAT RULES:
Return ONLY a valid JSON array of objects with the exact fields:
- "escena": Integer indicating the scene order.
- "duracion_seg": Estimated duration in seconds (integer).
- "narracion": The exact spoken text for the presenter/voiceover.
- "apoyo_visual": Description of what should be shown on screen (text, animations, B-roll).
- "fuentes": Array of sources as specified above.
