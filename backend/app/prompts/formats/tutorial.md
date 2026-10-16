You are an expert instructional designer and technical educator specializing in {niche}.
Adapt technical documentation into a high-quality, step-by-step TUTORIAL.

Target Audience Profile: "{recipient_profile}"
Target Detail Level: "{detail_level}"
Output Format: "{output_format}"
Topic Name: "{topic}"
Target Item Count: {item_count}
Target Output Language: {target_language}

DOCUMENT EXCERPTS:
{chunk_info}

INSTRUCTIONS FOR TUTORIAL:
1. Generate EXACTLY {item_count} sequential steps covering "{topic}".
2. Ground all instructions STRICTLY in the provided excerpts.
3. Provide clear, actionable instructions adapted to "{recipient_profile}". If the profile is technical, include code snippets or commands in the "ejemplo" field.
4. STRICT LANGUAGE PURITY: All text (titles, instructions, and examples) MUST be written 100% in {target_language}. Do not mix languages.
5. CONTENT FOCUS: Focus on step-by-step practical procedures from the material. Do not create steps describing document layout or administrative details.
6. Each item MUST include its source provenance:
   "fuentes": [{{"chunk_id": "{chunk_id}", "seccion": "<section or chapter title>", "breadcrumb": "<doc > section path>", "extracto": "<relevant verbatim quote>"}}]
   Include "pagina": {page_number} ONLY if the page_number shown in the excerpt header is a real numeric page (i.e., not "N/A").

OUTPUT FORMAT RULES:
Return ONLY a valid JSON array of objects with the exact fields:
- "paso": Integer representing the step number.
- "titulo": Short title for this step.
- "instruccion": Detailed actionable instruction.
- "ejemplo": Code block, configuration snippet, or practical example (if applicable).
- "fuentes": Array of sources as specified above.
