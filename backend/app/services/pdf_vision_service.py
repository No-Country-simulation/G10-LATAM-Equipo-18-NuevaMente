"""
pdf_vision_service.py

Purpose:
    Generates educational textual descriptions for extracted diagrams and images
    using multimodal LLMs following configured cascades and prompts.

Input:
    - image_records (List[Dict[str, Any]]): Metadata records of extracted images.

Output:
    - Formatted Markdown appendix string summarizing all analyzed visual figures.
"""

import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.infrastructure.llm.gemini_client import GeminiClient
from app.prompts.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


class PdfVisionService:
    """Processes extracted diagrams and generates structured text descriptions using multimodal models."""

    def __init__(self):
        self._gemini_client: Optional[GeminiClient] = None

    def _get_gemini_client(self) -> GeminiClient:
        """Instantiates or returns cached GeminiClient."""
        if self._gemini_client is None:
            self._gemini_client = GeminiClient()
        return self._gemini_client

    def describe_image(self, image_path: str) -> Optional[str]:
        """
        Sends an image to the configured vision cascade and returns its description.
        Returns None if vision is unavailable or the image lacks educational content.
        """
        try:
            prompt_instruction = load_prompt("diagram_vision.md")
        except Exception as exc:
            logger.warning("Failed to load diagram_vision.md: %s", exc)
            prompt_instruction = (
                "Describe this technical diagram or chart in detail, transcribing any readable text."
            )

        cascade = settings.LLM_CASCADES.get("vision_diagram", [
            {"provider": "gemini", "model": "gemini-2.5-flash"}
        ])

        for tier in cascade:
            provider = tier.get("provider")
            model_name = tier.get("model")

            if provider == "gemini":
                try:
                    client = self._get_gemini_client()
                    if not client.is_available:
                        continue

                    response_text = client.generate(
                        prompt="Provide a structured technical analysis of this image.",
                        system_instruction=prompt_instruction,
                        model_name=model_name,
                        image_path=image_path,
                    )

                    if not response_text:
                        continue

                    cleaned = response_text.strip()
                    if "NO_EDUCATIONAL_CONTENT" in cleaned:
                        return None
                    return cleaned
                except Exception as exc:
                    logger.warning(
                        "Vision call failed on tier provider=%s model=%s: %s",
                        provider,
                        model_name,
                        exc,
                    )
                    continue

        return None

    def build_visual_appendix(self, image_records: List[Dict[str, Any]]) -> str:
        """
        Processes a list of extracted images and formats successful descriptions into a Markdown appendix.
        """
        if not image_records:
            return ""

        descriptions: List[str] = []
        for record in image_records:
            image_path = record.get("path")
            page_number = record.get("page_number", 1)
            img_index = record.get("image_index", 1)

            if not image_path:
                continue

            try:
                desc = self.describe_image(image_path)
                if desc:
                    descriptions.append(
                        f"### Figure (Page {page_number}, Image {img_index})\n{desc}"
                    )
            except Exception as exc:
                logger.warning("Failed to describe image %s: %s", image_path, exc)

        if not descriptions:
            return ""

        appendix_header = "\n\n## Extracted Visual Context and Diagrams\n\n"
        return appendix_header + "\n\n".join(descriptions)
