"""Text chunking utility for mutual fund source documents."""

import re
from dataclasses import dataclass


@dataclass
class Chunk:
    chunk_index: int
    content: str
    metadata: dict


def chunk_text(
    text: str,
    source_id: str,
    max_tokens: int = 500,
    overlap_tokens: int = 50,
) -> list[Chunk]:
    """Split text into overlapping chunks of approximately max_tokens words.

    Uses a simple word-count heuristic (1 token ≈ 0.75 words).
    Splits on sentence boundaries when possible.
    """
    if not text or not text.strip():
        return []

    max_words = int(max_tokens * 0.75)
    overlap_words = int(overlap_tokens * 0.75)

    sentences = re.split(r'(?<=[.!?])\s+', text.strip())

    chunks: list[Chunk] = []
    current_sentences: list[str] = []
    current_word_count = 0
    chunk_idx = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        word_count = len(sentence.split())

        if current_word_count + word_count > max_words and current_sentences:
            content = " ".join(current_sentences)
            chunks.append(Chunk(
                chunk_index=chunk_idx,
                content=content,
                metadata={
                    "source_id": source_id,
                    "word_count": current_word_count,
                    "char_count": len(content),
                },
            ))
            chunk_idx += 1

            overlap_sentences = current_sentences
            overlap_wc = 0
            for s in reversed(overlap_sentences):
                wc = len(s.split())
                if overlap_wc + wc > overlap_words:
                    break
                overlap_wc += wc
            keep = []
            running = 0
            for s in reversed(overlap_sentences):
                wc = len(s.split())
                if running + wc > overlap_words:
                    break
                keep.insert(0, s)
                running += wc

            current_sentences = keep + [sentence]
            current_word_count = sum(len(s.split()) for s in current_sentences)
        else:
            current_sentences.append(sentence)
            current_word_count += word_count

    if current_sentences:
        content = " ".join(current_sentences)
        chunks.append(Chunk(
            chunk_index=chunk_idx,
            content=content,
            metadata={
                "source_id": source_id,
                "word_count": current_word_count,
                "char_count": len(content),
            },
        ))

    return chunks
