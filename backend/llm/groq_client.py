import logging
import time
from functools import lru_cache

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import traceable

from backend.config import settings
from backend.metrics import LLM_REQUESTS, LLM_ERRORS, LLM_LATENCY, LLM_FAILOVER_TOTAL, LLM_PROVIDER_REQUESTS

logger = logging.getLogger("smartrfp.llm")

try:
    from groq import RateLimitError, APIStatusError, APIError
except Exception:
    RateLimitError = APIStatusError = APIError = Exception


class LLMUnavailable(RuntimeError):
    """Raised when no configured LLM provider can serve a request."""

@lru_cache(maxsize=1)
def get_llm() -> ChatGroq:
    if not settings.GROQ_API_KEY:
        raise LLMUnavailable(
            "GROQ_API_KEY is not set. Add it to your .env before starting the backend."
        )
    return ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.2,
        max_tokens=4096,
        max_retries=2,
        timeout=60,
    )


@lru_cache(maxsize=1)
def get_failover_llm():
    if not settings.LLM_FAILOVER_ENABLED or not settings.OPENAI_API_KEY:
        return None
    try:
        from langchain_openai import ChatOpenAI
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "OPENAI_API_KEY is set but langchain-openai is not installed (%s); "
            "failover disabled. Run: pip install langchain-openai", exc)
        return None
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.2,
        max_tokens=4096,
        max_retries=2,
        timeout=60,
    )


def llm_available() -> bool:
    return bool(settings.GROQ_API_KEY)


def _reason(exc: Exception) -> str:
    text = str(exc)
    low = text.lower()
    if "413" in text or "too large" in low or "tokens per minute" in low or "tpm" in low:
        return ("Prompt too large for the current Groq rate-limit tier (tokens per "
                "minute). The request was auto-shrunk and retried; if this still "
                "fails, reduce content size or upgrade your Groq tier.")
    if isinstance(exc, RateLimitError) or "rate_limit" in low or "429" in text:
        return ("Groq rate limit / daily token quota reached. Switch GROQ_MODEL "
                "(e.g. llama-3.1-8b-instant) or wait for the quota to reset.")
    if "authentication" in low or "invalid api key" in low or "401" in text:
        return "Groq authentication failed — check GROQ_API_KEY."
    if "model" in low and ("not" in low or "decommission" in low):
        return "Groq model not available — check GROQ_MODEL."
    return f"Groq request failed: {text}"


def _is_too_large(exc: Exception) -> bool:
    text = str(exc).lower()
    return "413" in str(exc) or "too large" in text or "tokens per minute" in text or "tpm" in text


def _is_retryable_for_failover(exc: Exception) -> bool:
    text = str(exc).lower()
    return (
        isinstance(exc, (RateLimitError, APIStatusError, APIError))
        or "rate_limit" in text or "429" in text
        or "timeout" in text or "timed out" in text
        or "503" in text or "502" in text or "overloaded" in text
    )


@traceable(name="LLM Chat Call", run_type="llm")
def chat(system_prompt: str, user_prompt: str,
         temperature: float = 0.3, max_tokens: int = 900) -> str:
    LLM_REQUESTS.inc()
    start = time.perf_counter()

    def _call_groq(prompt: str) -> str:
        llm = get_llm().bind(temperature=temperature, max_tokens=max_tokens)
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]
        response = llm.invoke(messages)
        text = (response.content or "").strip()
        if not text:
            raise LLMUnavailable("Groq returned an empty response.")
        return text

    def _call_failover(prompt: str) -> str:
        llm = get_failover_llm()
        if llm is None:
            raise LLMUnavailable("No failover provider configured.")
        llm = llm.bind(temperature=temperature, max_tokens=max_tokens)
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]
        response = llm.invoke(messages)
        text = (response.content or "").strip()
        if not text:
            raise LLMUnavailable("Failover provider returned an empty response.")
        return text

    try:
        try:
            result = _call_groq(user_prompt)
            LLM_PROVIDER_REQUESTS.labels(provider="groq", outcome="success").inc()
            return result
        except LLMUnavailable:
            raise
        except Exception as exc:
            if _is_too_large(exc) and len(user_prompt) > 500:
                logger.warning("chat() payload too large (%d chars) — retrying with a "
                                "shrunk prompt.", len(user_prompt))
                try:
                    shrunk = user_prompt[: max(500, len(user_prompt) // 2)]
                    result = _call_groq(shrunk)
                    LLM_PROVIDER_REQUESTS.labels(provider="groq", outcome="success_shrunk").inc()
                    return result
                except Exception as exc2:  # noqa: BLE001
                    exc = exc2

            LLM_PROVIDER_REQUESTS.labels(provider="groq", outcome="error").inc()

            if _is_retryable_for_failover(exc) and get_failover_llm() is not None:
                logger.warning("Groq failed (%s) — failing over to OpenAI (%s).",
                                exc, settings.OPENAI_MODEL)
                LLM_FAILOVER_TOTAL.labels(from_provider="groq", to_provider="openai").inc()
                try:
                    result = _call_failover(user_prompt)
                    LLM_PROVIDER_REQUESTS.labels(provider="openai", outcome="success").inc()
                    return result
                except Exception as exc3:  # noqa: BLE001
                    LLM_PROVIDER_REQUESTS.labels(provider="openai", outcome="error").inc()
                    logger.warning("OpenAI failover also failed: %s", exc3)
                    raise LLMUnavailable(_reason(exc3)) from exc3

            logger.warning("chat() failed: %s", exc)
            raise LLMUnavailable(_reason(exc)) from exc
    finally:
        LLM_LATENCY.observe(time.perf_counter() - start)