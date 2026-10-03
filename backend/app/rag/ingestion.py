from __future__ import annotations

import os


def extract_text(path: str) -> str:
    """Extract raw text from a supported document (PDF, TXT, MD)."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".txt", ".md"):
        with open(path, encoding="utf-8") as f:
            return f.read()
    if ext == ".pdf":
        import pypdf

        reader = pypdf.PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    raise ValueError(f"Unsupported document type: {ext}. Supported: .pdf, .txt, .md")


def load_directory(directory: str) -> list[tuple[str, str]]:
    """Return [(source_path, raw_text), ...] for every supported document in directory."""
    docs = []
    for fname in sorted(os.listdir(directory)):
        ext = os.path.splitext(fname)[1].lower()
        if ext in (".txt", ".md", ".pdf"):
            path = os.path.join(directory, fname)
            docs.append((path, extract_text(path)))
    return docs
