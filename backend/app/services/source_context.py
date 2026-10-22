"""source_context.py

Purpose:
    Single source of truth for how much of a document chunk is shown to the
    LLM stages (writer, critic and repair). Keeping one helper avoids the old
    behaviour where the writer, critic and repair stages independently cut the
    same chunk at 600, 400 and 500 characters respectively.

    When a chunk fits in the budget it is returned untouched. When it does not,
    the window is centred on an optional focus excerpt and aligned to sentence
    or word boundaries, so the model never receives a half-word or a cut in the
    middle of a sentence.
"""

from typing import Optional

from app.core.config import settings


# RAG_CONTEXT_SNIPPET_SIZE is the project-wide context budget. Parent chunks
# default to 1000 chars, so with this budget they are normally delivered whole.
SOURCE_CONTEXT_MAX_CHARS = int(getattr(settings, "RAG_CONTEXT_SNIPPET_SIZE", 1500))


def _align_start(text: str, start: int) -> int:
    """Moves a window start forward to the next word boundary."""
    if start <= 0:
        return 0
    while start < len(text) and not text[start].isspace():
        start += 1
    while start < len(text) and text[start].isspace():
        start += 1
    return start


def _align_end(text: str, end: int) -> int:
    """Moves a window end back to the last sentence or word boundary."""
    if end >= len(text):
        return len(text)
    sentence = text.rfind(". ", 0, end)
    if sentence >= max(0, end - 200):
        return sentence + 1
    while end > 0 and not text[end - 1].isspace():
        end -= 1
    return end


def select_source_context(
    text: str,
    max_chars: Optional[int] = None,
    focus: Optional[str] = None,
) -> str:
    """Returns a complete chunk when it fits, or a boundary-safe window.

    Args:
        text: Raw chunk content.
        max_chars: Budget in characters. Defaults to the project-wide value.
        focus: Optional excerpt used to centre the window when the chunk is
            larger than the budget.
    """
    clean = (text or "").strip()
    if not clean:
        return ""

    budget = max(200, int(max_chars or SOURCE_CONTEXT_MAX_CHARS))
    if len(clean) <= budget:
        return clean

    lower = clean.lower()
    focus_clean = (focus or "").strip()
    focus_index = lower.find(focus_clean.lower()[:200]) if focus_clean else -1

    if focus_index >= 0:
        start = max(0, focus_index - budget // 3)
        end = min(len(clean), start + budget)
        start = max(0, end - budget)
        start = _align_start(clean, start)
        end = _align_end(clean, end)
    else:
        start = 0
        end = _align_end(clean, budget)

    window = clean[start:end].strip()
    return window or clean[:budget].strip()
