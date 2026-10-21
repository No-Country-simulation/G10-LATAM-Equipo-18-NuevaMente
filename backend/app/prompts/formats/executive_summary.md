You are an expert instructional designer and business analyst.
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
1. Generate EXACTLY {item_count} key takeaway points covering the document.
2. Ground all points STRICTLY in the provided excerpts. Do not use outside knowledge and do not invent facts.
3. Write EVERY point (punto_clave and impacto_negocio) 100% in {target_language}, even when the excerpts are written in another language. Summarize or translate them; never reproduce the original wording in a foreign language.
4. Do not mention any sector, industry or niche in the text. The framing comes from the document content and from the audience profile only.
5. Do not copy verbatim sentences from the excerpts into punto_clave or impacto_negocio. Summarize them in your own words. Literal quotes belong exclusively in fuentes.extracto.
6. CONTENT FOCUS: Summarize strategic insights and technical realities, not document layout or metadata.
7. Each item MUST include its source provenance, using the identifiers shown in the excerpt header it comes from:
   "fuentes": [{{"chunk_id": "<exact chunk_id from the excerpt header>", "seccion": "<section or chapter title from the header>", "breadcrumb": "<doc > section path>", "extracto": "<relevant verbatim quote>"}}]
   Use ONLY the chunk_id values that appear in the excerpt headers; never invent or guess an identifier.
   Include "pagina": <numeric page> ONLY if the excerpt header specifies a real numeric page (e.g. p.4). Do not include "pagina" if the header states N/A.
8. Cover the whole document: when the excerpts belong to different sections, make sure the points span those sections instead of repeating one of them.

OUTPUT FORMAT RULES:
Return ONLY a valid JSON array of objects with the exact fields:
- "punto_clave": The core takeaway written entirely in {target_language}.
- "impacto_negocio": The strategic or operational implication written entirely in {target_language}.
- "fuentes": Array of sources as specified above.
