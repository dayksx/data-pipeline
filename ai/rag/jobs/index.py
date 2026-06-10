"""RAG index job — like spark/jobs/analysis.py (logic + __main__ in one place)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import psycopg
from langchain_openai import OpenAIEmbeddings

# Allow: from chunking import ... and from insights_agent.config import ...
_JOBS_DIR = Path(__file__).resolve().parent
_AI_SRC = _JOBS_DIR.parents[1] / "src"
sys.path.insert(0, str(_JOBS_DIR))
sys.path.insert(0, str(_AI_SRC))

from chunking import load_all_chunks  # noqa: E402
from insights_agent.config import get_settings  # noqa: E402


def index_documents() -> dict:
    settings = get_settings()
    chunks = load_all_chunks(settings.rag_docs_dir)
    if not chunks:
        return {"indexed": 0, "error": "no_documents"}

    embedder = OpenAIEmbeddings(
        model = settings.embedding_model,
        api_key = settings.llm_api_key,
    )
    vectors = embedder.embed_documents([c.content for c in chunks])

    with psycopg.connect(settings.postgres_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE public.rag_chunks")
            for chunk, vector in zip(chunks, vectors):
                cur.execute(
                    """
                    INSERT INTO public.rag_chunks
                        (chunk_id, source, section, content, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (chunk.chunk_id, chunk.source, chunk.section, chunk.content, vector),
                )
        conn.commit()

    return {"indexed": len(chunks), "sources": sorted({c.source for c in chunks})}


def main() -> None:
    print(json.dumps(index_documents(), indent=2))


if __name__ == "__main__":
    main()
