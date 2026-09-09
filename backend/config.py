import os
from functools import lru_cache
from typing import Annotated, Dict, List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ---- App -----------------------------------------------------------
    APP_NAME: str = "SmartRFP"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = False

    # ---- Groq (primary LLM) ---------------------------------------------
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    # ---- OpenAI (optional failover LLM) ----------------------------------
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    LLM_FAILOVER_ENABLED: bool = True

    # ---- Pinecone ---------------------------------------------------------
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "smartrfp"
    PINECONE_REGION: str = "us-east-1"
    PINECONE_CLOUD: str = "aws"
    PINECONE_METRIC: str = "cosine"

    # ---- Embeddings ---------------------------------------------------------
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # ---- RAG retrieval ------------------------------------------------------
    RAG_TOP_K: int = 5
    RAG_SCORE_THRESHOLD: float = 0.30

    # ---- Tavily (optional live pricing/web search) --------------------------
    TAVILY_API_KEY: str = ""

    # ---- PostgreSQL -----------------------------------------------------
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/SmartRFP"

    # ---- LangSmith tracing ------------------------------------------------
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "smartrfp"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"

    # ---- API security -------------------------------------------------------
    API_KEYS: Annotated[Dict[str, str], NoDecode] = {}
    REQUIRE_AUTH: bool = False

    # ---- CORS -----------------------------------------------------------
    ALLOWED_ORIGINS: Annotated[List[str], NoDecode] = ["http://localhost:8501"]

    # ---- Rate limiting --------------------------------------------------
    RATE_LIMIT_DEFAULT: str = "60/minute"
    RATE_LIMIT_UPLOAD: str = "10/minute"
    RATE_LIMIT_STORAGE_URI: str = "memory://"

    # ---- Guardrails -------------------------------------------------------
    GUARDRAILS_STRICT: bool = True

    # ---- Evaluation / RAGAS ----------------------------------------------
    RAGAS_MAX_SAMPLES: int = 4
    RAGAS_MAX_RETRIES: int = 2
    RAGAS_RETRY_BACKOFF_SECONDS: float = 5
    RAGAS_TIMEOUT_SECONDS: int = 120
    EVAL_MIN_FAITHFULNESS: float = 0.60
    EVAL_MIN_ANSWER_RELEVANCY: float = 0.50
    EVAL_MIN_CONTEXT_PRECISION: float = 0.40
    EVAL_MIN_CONTEXT_RECALL: float = 0.30
    EVAL_MIN_COMPLETENESS: float = 0.70

    # ---- Frontend <-> backend (HTTP) -------------------------------------
    SMARTRFP_API_URL: str = "http://localhost:8000"
    #SMARTRFP_API_URL: str = "https://smartrfp-production.up.railway.app"
    SMARTRFP_API_KEY: str = ""

    # ---- Exports ----------------------------------------------------------
    EXPORTS_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports")

    # ---- Grafana (docker-compose only; read here so it's never an "extra"
    GRAFANA_ADMIN_USER: str = "admin"
    GRAFANA_ADMIN_PASSWORD: str = ""

    # ------------------------------------------------------------------ #
    # Parsing
    # ------------------------------------------------------------------ #
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("API_KEYS", mode="before")
    @classmethod
    def _parse_api_keys(cls, v):
        """'abc123,def456:reviewer,ghi789:viewer' -> {'abc123': 'admin', ...}."""
        if isinstance(v, dict):
            return v
        result: Dict[str, str] = {}
        if not v:
            return result
        for raw in str(v).split(","):
            item = raw.strip()
            if not item:
                continue
            if ":" in item:
                key, role = item.split(":", 1)
                result[key.strip()] = (role.strip() or "admin").lower()
            else:
                result[item] = "admin"
        return result

    @model_validator(mode="after")
    def _default_require_auth(self):
        raw = os.getenv("REQUIRE_AUTH")
        if raw is None or raw.strip() == "":
            object.__setattr__(self, "REQUIRE_AUTH", self.ENVIRONMENT == "production")
        return self


@lru_cache
def get_settings() -> "Settings":
    s = Settings()
    os.makedirs(s.EXPORTS_DIR, exist_ok=True)
    return s


settings = get_settings()