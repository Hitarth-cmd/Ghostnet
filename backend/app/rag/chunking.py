from __future__ import annotations


def chunk_text(text: str, chunk_size_chars: int = 800, overlap_chars: int = 120) -> list[str]:
    """
    Simple, deterministic character-window chunker with overlap. Splits on
    paragraph boundaries where possible to avoid cutting mid-sentence.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size_chars:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) > chunk_size_chars:
                # Hard-split an overlong paragraph.
                start = 0
                while start < len(para):
                    end = start + chunk_size_chars
                    chunks.append(para[start:end])
                    start = end - overlap_chars
                current = ""
            else:
                current = para

    if current:
        chunks.append(current)

    # Apply overlap between consecutive chunks for better retrieval recall.
    overlapped = []
    for i, c in enumerate(chunks):
        if i == 0:
            overlapped.append(c)
        else:
            prefix = chunks[i - 1][-overlap_chars:] if overlap_chars else ""
            overlapped.append(f"{prefix} {c}".strip())
    return overlapped
