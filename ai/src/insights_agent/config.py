from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ai/semantic/ — sibling of ai/src/
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
SEMANTIC_DIR = Path(__file__).resolve().parents[2] / "semantic"
RAG_DOCS_DIR = Path(__file__).resolve().parents[2] / "rag" / "docs"

ALLOWED_TABLES = frozenset({
    "sales_clean",
    "total_revenue",
    "top_products",
    "monthly_sales",
    "monthly_stats",
})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        extra="ignore",
    )

    semantic_dir: Path = SEMANTIC_DIR

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "pipeline"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"

    llm_api_key: str = Field(default="", validation_alias="LLM_API_KEY")
    llm_model: str = Field(default="gpt-4o-mini", validation_alias="LLM_MODEL")

    sql_max_rows: int = 500
    sql_timeout_seconds: int = 10

    embedding_model: str = Field(
        default="text-embedding-3-small",
        validation_alias="EMBEDDING_MODEL",
    )
    rag_top_k: int = Field(default=4, validation_alias="RAG_TOP_K")
    rag_docs_dir: Path = RAG_DOCS_DIR

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

        


@lru_cache
def get_settings() -> Settings:
    # LangChain/LangSmith read os.environ — pydantic alone does not export .env.
    load_dotenv(ENV_FILE, override=False)
    return Settings()
