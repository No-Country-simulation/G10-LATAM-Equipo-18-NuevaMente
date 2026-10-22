"""
test_chunking_contract.py

Purpose:
    Contract tests for the chunking layer, written before changing the
    implementation. They describe the guarantees the rest of the RAG pipeline
    already assumes:

      1. Adjacent chunks produced from paragraph-packed content share the
         configured overlap. Today they share zero, because `chunk_text()`
         only applies `overlap` when a single paragraph is larger than the
         chunk size (`ingester_service.py:413-426`).
      2. Every chunk respects the configured maximum size.
      3. The same guarantee holds for child chunks, which are the units
         actually embedded and retrieved.

    These tests are permanent regression coverage for the overlap-aware
    chunking implementation: they were RED against ac7833d and now guard the
    contract on every change.
"""

import pytest

from app.services.ingester_service import IngesterService


def _boundary_overlap(left: str, right: str) -> int:
    """Returns how many trailing chars of `left` are the prefix of `right`."""
    for size in range(min(len(left), len(right)), 0, -1):
        if left[-size:] == right[:size]:
            return size
    return 0


def _paragraphs(count: int, words_per_paragraph: int = 18) -> str:
    """Builds distinct paragraphs, each comfortably smaller than a chunk, so
    the splitter has to pack several of them per chunk."""
    paragraphs = []
    for index in range(count):
        body = " ".join(f"p{index}w{word}" for word in range(words_per_paragraph))
        paragraphs.append(f"Parrafo {index}: {body}.")
    return "\n\n".join(paragraphs)


@pytest.mark.parametrize(
    "size, overlap",
    [
        (300, 60),  # parent-size scenario
        (160, 40),  # child-size scenario
    ],
)
def test_paragraph_packed_chunks_keep_the_configured_overlap(size: int, overlap: int) -> None:
    """Every frontier between packed chunks must carry the configured overlap.

    A small tolerance is allowed because an implementation may snap the
    overlap window to a word boundary, but the current 0-char behaviour must
    fail this test.
    """
    service = IngesterService(parent_chunk_size=size, child_chunk_size=size, overlap=overlap, child_overlap=overlap)
    chunks = service.chunk_text(_paragraphs(12), chunk_size=size, overlap=overlap)

    assert len(chunks) >= 3, "the fixture must force several chunk boundaries"
    overlaps = [
        _boundary_overlap(chunks[index], chunks[index + 1])
        for index in range(len(chunks) - 1)
    ]

    # Word-boundary snapping and the size budget can shorten the window when
    # the next paragraph already consumes most of the chunk. Require a clear
    # majority of the configured overlap instead of byte-exact boundaries.
    minimum = max(1, int(overlap * 0.6))
    assert min(overlaps) >= minimum, (
        f"chunk frontiers do not carry the configured overlap: "
        f"expected >= {minimum} chars, got {overlaps}"
    )


@pytest.mark.parametrize("size", [300, 160])
def test_chunks_never_exceed_the_configured_size(size: int) -> None:
    """The overlap must be carried inside the size budget, not on top of it."""
    service = IngesterService(parent_chunk_size=size, child_chunk_size=size, overlap=30, child_overlap=30)
    chunks = service.chunk_text(_paragraphs(12), chunk_size=size, overlap=30)

    assert chunks, "the fixture must produce chunks"
    assert max(len(chunk) for chunk in chunks) <= size
