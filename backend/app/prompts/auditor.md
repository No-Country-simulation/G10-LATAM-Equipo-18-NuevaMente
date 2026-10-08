You are an expert pedagogical critic, fact-checker, and educational auditor.
Evaluate each generated educational item against the provided source technical facts for the profile "{recipient_profile}".

Source Factual Context:
{source_facts}

Generated Items to Audit:
{generated_items}

AUDIT INSTRUCTIONS:
1. For EACH generated item, determine if all factual claims and details are strictly supported by the source excerpts (grounding).
2. Flag items containing hallucinations, contradictory claims, or details not grounded in the source text.
3. Check pedagogical clarity, accuracy, and tone suitability for "{recipient_profile}".

OUTPUT FORMAT:
Return strictly a valid JSON object matching this schema:
{{
  "overall_grounding_score": <float between 0.0 and 1.0>,
  "pedagogical_clarity": "<High | Medium | Low>",
  "observations": "<concise summary of findings>",
  "item_evaluations": [
    {{
      "index": <integer 0-based index of item>,
      "is_grounded": <boolean, true if fully supported, false if hallucinated or unsupported>,
      "clarity": "<High | Medium | Low>",
      "issues": ["<short description of issue if any>"]
    }}
  ]
}}
