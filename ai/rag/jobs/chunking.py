from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source: str
    section: str
    content: str


def _make_chunk_id(source: str, section: str) -> str:
    raw = f"{source}::{section}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def chunk_markdown_file(path: Path) -> list[Chunk]:
    text = path.read_text(encoding="utf-8")
    source = path.name
    chunks: list[Chunk] = []
    current_section = "Introduction"
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    chunks.append(Chunk(
                        chunk_id=_make_chunk_id(source, current_section),
                        source=source,
                        section=current_section,
                        content=content,
                    ))
            current_section = line[3:].strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            chunks.append(Chunk(
                chunk_id=_make_chunk_id(source, current_section),
                source=source,
                section=current_section,
                content=content,
            ))

    return chunks


def load_all_chunks(docs_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(docs_dir.glob("*.md")):
        chunks.extend(chunk_markdown_file(path))
    return chunks
