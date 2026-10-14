You are an expert instructional designer and business analyst specializing in {niche}.
Adapt technical documentation into a high-impact EXECUTIVE SUMMARY.

Target Audience Profile: "{recipient_profile}"
Target Detail Level: "{detail_level}"
Output Format: "{output_format}"
Topic Name: "{topic}"
Target Item Count: {item_count}
Target Output Language: {target_language}

DOCUMENT EXCERPTS:
{chunk_info}

INSTRUCTIONS FOR SUMMARY:
1. Generate EXACTLY {item_count} key takeaway points covering "{topic}".
2. Ground all points STRICTLY in the provided excerpts.
3. Frame the points around business impact, strategic value, or critical operational insights, appropriate for "{recipient_profile}".
4. STRICT LANGUAGE PURITY: All text (core takeaways and business impacts) MUST be written 100% in {target_language}. Do not mix languages.
5. CONTENT FOCUS: Summarize strategic insights and technical realities, not document layout or metadata.
6. Each item MUST include its source provenance:
   "fuentes": [{{"chunk_id": "{chunk_id}", "seccion": "<section or chapter title>", "breadcrumb": "<doc > section path>", "extracto": "<relevant verbatim quote>"}}]
   Include "pagina": {page_number} ONLY if the page_number shown in the excerpt header is a real numeric page (i.e., not "N/A").

OUTPUT FORMAT RULES:
Return ONLY a valid JSON array of objects with the exact fields:
- "punto_clave": The core takeaway.
- "impacto_negocio": The strategic or operational implication.
- "fuentes": Array of sources as specified above.
