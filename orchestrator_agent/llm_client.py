"""LLM client for the Planner Agent.

Provider routing:
  - azure/<deployment>  →  openai.AzureOpenAI  (no litellm needed)
  - anything else       →  litellm (if installed) or openai.OpenAI
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

_AZURE_MAX_RETRIES = 3          # retry on transient network failures
_AZURE_RETRY_DELAY_SEC = 1.5    # base delay; doubles each attempt

from orchestrator_agent.config import LLMConfig

logger = logging.getLogger(__name__)


def call_llm(messages: list[dict[str, Any]], config: LLMConfig) -> str:
    """Call the configured LLM and return the response text.

    Uses openai.AzureOpenAI directly for azure/* models (no extra dependency).
    Falls back to litellm for all other providers.
    """
    if config.model.startswith("azure/"):
        return _call_azure(messages, config)
    return _call_litellm(messages, config)


def call_llm_json(messages: list[dict[str, Any]], config: LLMConfig) -> dict[str, Any]:
    """Call the LLM and parse the response as JSON.

    Strips markdown code fences before parsing.
    Raises ValueError if the response is not valid JSON.
    """
    raw = call_llm(messages, config)

    clean = raw.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        clean = "\n".join(line for line in lines if not line.startswith("```")).strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError as exc:
        logger.warning("llm_json_parse_failed raw=%r error=%s", raw[:200], exc)
        raise ValueError(f"LLM did not return valid JSON: {exc}") from exc


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _call_azure(messages: list[dict[str, Any]], config: LLMConfig) -> str:
    """Call Azure OpenAI using the openai SDK's AzureOpenAI client.

    The model string must be "azure/<deployment-name>". The deployment name
    is extracted and used as the model parameter for the Azure API.

    Proxy: reads HTTPS_PROXY / HTTP_PROXY from the environment and passes them
    explicitly to the underlying httpx client so corporate proxies are honoured
    even when the OS proxy registry is not configured.
    """
    try:
        import httpx
        from openai import AzureOpenAI
    except ImportError as exc:
        raise RuntimeError(
            "openai package is required for Azure OpenAI calls: pip install openai"
        ) from exc

    deployment = config.model[len("azure/"):]   # "azure/gpt-4o" → "gpt-4o"
    api_version = os.getenv("AZURE_API_VERSION", "2024-02-01")

    if not config.api_base:
        raise RuntimeError(
            "PLANNER_LLM_API_BASE is required for Azure OpenAI "
            "(e.g. https://my-resource.openai.azure.com/)"
        )
    if not config.api_key:
        raise RuntimeError("PLANNER_LLM_API_KEY is required for Azure OpenAI")

    # Proxy disabled for all Azure calls: trust_env=False prevents httpx from
    # reading OS/shell proxy vars; no proxy= arg means direct connection.
    # Azure private endpoints require a direct route from the allowed network.
    http_client = httpx.Client(trust_env=False)

    logger.debug(
        "azure_llm_call deployment=%s api_version=%s endpoint=%s proxy=disabled",
        deployment, api_version, config.api_base,
    )

    client = AzureOpenAI(
        api_key=config.api_key,
        api_version=api_version,
        azure_endpoint=config.api_base,
        http_client=http_client,
    )

    last_exc: Exception | None = None
    for attempt in range(_AZURE_MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=deployment,
                messages=messages,  # type: ignore[arg-type]
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as exc:
            last_exc = exc
            err_str = str(exc)
            # Retry on transient network / gateway errors; give up immediately
            # on auth failures (401) or content policy (400).
            is_transient = (
                "403" in err_str        # intermittent private-endpoint routing
                or "429" in err_str     # rate limit
                or "500" in err_str     # upstream server error
                or "502" in err_str
                or "503" in err_str
                or "timeout" in err_str.lower()
                or "connection" in err_str.lower()
            )
            if is_transient and attempt < _AZURE_MAX_RETRIES - 1:
                delay = _AZURE_RETRY_DELAY_SEC * (2 ** attempt)
                logger.warning(
                    "azure_retry attempt=%d/%d error=%s retrying_in=%.1fs",
                    attempt + 1, _AZURE_MAX_RETRIES, err_str[:120], delay,
                )
                time.sleep(delay)
            else:
                break

    raise RuntimeError(f"Azure OpenAI call failed after {_AZURE_MAX_RETRIES} attempts: {last_exc}") from last_exc


def _call_litellm(messages: list[dict[str, Any]], config: LLMConfig) -> str:
    """Call any non-Azure provider via litellm."""
    try:
        from litellm import completion
    except ImportError as exc:
        raise RuntimeError(
            "litellm is required for non-Azure LLM calls: pip install litellm"
        ) from exc

    kwargs: dict[str, Any] = {
        "model": config.model,
        "messages": messages,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
    if config.api_base:
        kwargs["api_base"] = config.api_base
    if config.api_key:
        kwargs["api_key"] = config.api_key

    try:
        response = completion(**kwargs)
    except Exception as exc:
        raise RuntimeError(f"LLM call failed: {exc}") from exc

    return (response.choices[0].message.content or "").strip()
