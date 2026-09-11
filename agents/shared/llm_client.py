from __future__ import annotations

import logging
import os
from typing import Optional
from dotenv import load_dotenv
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_groq import ChatGroq

load_dotenv()

logger = logging.getLogger(__name__)

# Shared process-wide rate limiter to prevent concurrent agent bursts from exceeding Groq RPM limits
# Max 0.33 requests per second (1 request every 3 seconds) with a burst capacity of 1 request
_shared_rate_limiter = InMemoryRateLimiter(
    requests_per_second=0.33,
    check_every_n_seconds=0.1,
    max_bucket_size=1,
)

def get_groq_llm(
    model: Optional[str] = None,
    temperature: float = 0.0,
    max_retries: int = 2,
    requests_per_second: Optional[float] = None,
) -> ChatGroq:
    """
    Returns a configured ChatGroq instance equipped with shared rate-limiting
    and automatic retry backoff to eliminate HTTP 429 errors.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set.")

    # Resolve model hierarchy: explicitly passed model -> GROQ_MODEL -> RESPONSE_AGENT_MODEL -> Default fallback
    resolved_model = (
        model
        or os.getenv("GROQ_MODEL")
        or os.getenv("RESPONSE_AGENT_MODEL")
        or "openai/gpt-oss-20b"
    )

    rate_limiter = (
        InMemoryRateLimiter(
            requests_per_second=requests_per_second,
            check_every_n_seconds=0.1,
            max_bucket_size=2,
        )
        if requests_per_second is not None
        else _shared_rate_limiter
    )

    logger.debug("Initializing ChatGroq instance model=%s temperature=%.2f", resolved_model, temperature)

    return ChatGroq(
    model=resolved_model,
    temperature=temperature,
    max_tokens=int(os.getenv("GROQ_MAX_OUTPUT_TOKENS", "1000")),
    api_key=api_key,
    max_retries=min(max_retries, 2),
    rate_limiter=rate_limiter,
)