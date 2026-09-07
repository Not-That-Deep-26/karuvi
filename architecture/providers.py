"""
Universal AI Model Provider Connection Layer
============================================

Supports connecting to user-selected AI providers and models:
- Google Gemini (REST / google-genai)
- OpenAI (GPT-4o, GPT-4o-mini, o3-mini)
- OpenRouter (Claude 3.5 Sonnet, DeepSeek R1, Llama 3.3, etc.)
- Ollama (local offline models: Llama 3.1, DeepSeek R1, Qwen 2.5 Coder)
- Anthropic (Claude 3.5 Sonnet)
- Custom OpenAI-compatible endpoints (vLLM, LMStudio, LocalAI)

Uses standard library HTTP networking with automatic fallbacks and retries.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("karuvi.architecture.providers")


DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o",
    "openrouter": "anthropic/claude-3.5-sonnet",
    "ollama": "llama3.1",
    "anthropic": "claude-3-5-sonnet-20241022",
    "custom": "default",
}


@dataclass
class AIProviderConfig:
    """Configuration for AI model and provider connection."""
    provider: str = "auto"
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.2
    max_tokens: int = 4096
    timeout_seconds: int = 60

    def resolve(self) -> AIProviderConfig:
        """Resolves auto-detected providers, API keys, and models from environment."""
        provider = (self.provider or "auto").lower()

        # Detect provider from env if auto
        if provider == "auto":
            if os.environ.get("AI_PROVIDER"):
                provider = os.environ["AI_PROVIDER"].lower()
            elif os.environ.get("GEMINI_API_KEY"):
                provider = "gemini"
            elif os.environ.get("OPENAI_API_KEY"):
                provider = "openai"
            elif os.environ.get("OPENROUTER_API_KEY"):
                provider = "openrouter"
            elif os.environ.get("ANTHROPIC_API_KEY"):
                provider = "anthropic"
            else:
                provider = "gemini"

        api_key = self.api_key
        if not api_key:
            if provider == "gemini":
                api_key = os.environ.get("GEMINI_API_KEY")
            elif provider == "openai":
                api_key = os.environ.get("OPENAI_API_KEY")
            elif provider == "openrouter":
                api_key = os.environ.get("OPENROUTER_API_KEY")
            elif provider == "anthropic":
                api_key = os.environ.get("ANTHROPIC_API_KEY")

        base_url = self.base_url
        if not base_url:
            if provider == "ollama":
                base_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            elif provider == "openai" and os.environ.get("OPENAI_BASE_URL"):
                base_url = os.environ.get("OPENAI_BASE_URL")

        model = self.model or os.environ.get("AI_MODEL") or DEFAULT_MODELS.get(provider, "default")

        return AIProviderConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout_seconds=self.timeout_seconds,
        )


def _http_post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    """Execute HTTP POST with JSON body and parse response."""
    data_bytes = json.dumps(payload).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, data=data_bytes, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        logger.error(f"HTTP error {e.code} from {url}: {err_msg}")
        raise RuntimeError(f"API request failed with HTTP {e.code}: {err_msg}") from e
    except Exception as e:
        logger.error(f"Request failed to {url}: {e}")
        raise RuntimeError(f"Network error calling {url}: {e}") from e


def _call_gemini(prompt: str, config: AIProviderConfig) -> str:
    """Call Google Gemini API."""
    # First try google-genai SDK if available
    try:
        from google import genai
        client = genai.Client(api_key=config.api_key) if config.api_key else genai.Client()
        response = client.models.generate_content(
            model=config.model or "gemini-2.5-flash",
            contents=prompt,
        )
        if response and response.text:
            return response.text
    except Exception as sdk_err:
        logger.debug(f"google-genai SDK call fallback to REST: {sdk_err}")

    # Fallback to REST API
    api_key = config.api_key
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable or config.api_key is required for Gemini provider.")

    model = config.model or "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": config.temperature,
            "maxOutputTokens": config.max_tokens,
        },
    }
    res = _http_post_json(url, payload, timeout=config.timeout_seconds)
    candidates = res.get("candidates", [])
    if candidates and "content" in candidates[0]:
        parts = candidates[0]["content"].get("parts", [])
        if parts and "text" in parts[0]:
            return parts[0]["text"]
    raise RuntimeError(f"Unexpected Gemini response structure: {res}")


def _call_openai(prompt: str, config: AIProviderConfig) -> str:
    """Call OpenAI API or custom OpenAI-compatible endpoint."""
    api_key = config.api_key or "dummy"
    base_url = (config.base_url or "https://api.openai.com/v1").rstrip("/")
    url = f"{base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": config.model or "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
    res = _http_post_json(url, payload, headers=headers, timeout=config.timeout_seconds)
    choices = res.get("choices", [])
    if choices and "message" in choices[0]:
        return choices[0]["message"].get("content", "")
    raise RuntimeError(f"Unexpected OpenAI response structure: {res}")


def _call_openrouter(prompt: str, config: AIProviderConfig) -> str:
    """Call OpenRouter API."""
    api_key = config.api_key
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable or config.api_key is required for OpenRouter.")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/karuvi",
        "X-Title": "Karuvi Architecture Cartography",
    }
    payload = {
        "model": config.model or "anthropic/claude-3.5-sonnet",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
    res = _http_post_json(url, payload, headers=headers, timeout=config.timeout_seconds)
    choices = res.get("choices", [])
    if choices and "message" in choices[0]:
        return choices[0]["message"].get("content", "")
    raise RuntimeError(f"Unexpected OpenRouter response structure: {res}")


def _call_ollama(prompt: str, config: AIProviderConfig) -> str:
    """Call local Ollama service."""
    base_url = (config.base_url or "http://localhost:11434").rstrip("/")
    url = f"{base_url}/api/generate"
    payload = {
        "model": config.model or "llama3.1",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": config.temperature,
            "num_predict": config.max_tokens,
        },
    }
    res = _http_post_json(url, payload, timeout=config.timeout_seconds)
    if "response" in res:
        return res["response"]
    raise RuntimeError(f"Unexpected Ollama response structure: {res}")


def _call_anthropic(prompt: str, config: AIProviderConfig) -> str:
    """Call Anthropic Messages API."""
    api_key = config.api_key
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable or config.api_key is required for Anthropic.")

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": config.model or "claude-3-5-sonnet-20241022",
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    res = _http_post_json(url, payload, headers=headers, timeout=config.timeout_seconds)
    content = res.get("content", [])
    if content and "text" in content[0]:
        return content[0]["text"]
    raise RuntimeError(f"Unexpected Anthropic response structure: {res}")


def generate_completion(prompt: str, config: AIProviderConfig | None = None) -> str:
    """
    Executes a model completion using the specified AI provider.
    """
    resolved = (config or AIProviderConfig()).resolve()
    provider = resolved.provider

    logger.info(f"[providers] Prompting {provider} model={resolved.model}")

    if provider == "gemini":
        return _call_gemini(prompt, resolved)
    elif provider in ("openai", "custom"):
        return _call_openai(prompt, resolved)
    elif provider == "openrouter":
        return _call_openrouter(prompt, resolved)
    elif provider == "ollama":
        return _call_ollama(prompt, resolved)
    elif provider == "anthropic":
        return _call_anthropic(prompt, resolved)
    else:
        raise ValueError(f"Unsupported AI provider: {provider}")


def is_provider_configured(config: AIProviderConfig | None = None) -> bool:
    """Returns True if the resolved provider has valid credentials/endpoint."""
    resolved = (config or AIProviderConfig()).resolve()
    if resolved.provider == "ollama":
        # Check if Ollama endpoint responds
        try:
            url = f"{(resolved.base_url or 'http://localhost:11434').rstrip('/')}/api/tags"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2):
                return True
        except Exception:
            return False
    elif resolved.provider == "custom":
        return bool(resolved.base_url)
    else:
        return bool(resolved.api_key)
