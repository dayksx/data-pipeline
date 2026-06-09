from dataclasses import dataclass
import hashlib
from pathlib import Path
from signal import strsignal

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
            # Save the previous chunk if this is not the first section
            if current_lines:
               # Join the current lines with a space between each line
                content = "\n".join(current_lines).strip()
                # Create the chunk if there is content
                if content:
                    chunks.append(Chunk(
                        chunk_id=_make_chunk_id(source, current_section),
                        source=source,
                        section=current_section,
                        content=content,
                    ))
            # Start a new section
            current_section = line[3:].strip()
            current_lines = [line]
        # Stack a new line
        else:
            current_lines.append(line)

    # Add the last chunk if there is content
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
        chunks.extend(chunk_markdow_file(path))
    return chunks
