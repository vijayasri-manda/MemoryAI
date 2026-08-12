"""
LLM service abstraction supporting streaming and multiple providers.
Providers: OpenAI, Anthropic Claude, Google Gemini, Ollama (local), and Mock/Dev mode.
"""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from app.core.config import settings
from app.core.exceptions import LLMError
from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Message type ──────────────────────────────────────────────────────────────

class ChatMessage:
    def __init__(self, role: str, content: str):
        self.role = role      # "system" | "user" | "assistant"
        self.content = content

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


# ── Abstract Base ──────────────────────────────────────────────────────────────

class BaseLLMService(ABC):
    @abstractmethod
    async def complete(self, messages: list[ChatMessage]) -> str:
        """Return a single complete response string."""
        ...

    @abstractmethod
    async def stream(self, messages: list[ChatMessage]) -> AsyncGenerator[str, None]:
        """Yield response chunks as they arrive (for SSE streaming)."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...


# ── Mock/Dev LLM ───────────────────────────────────────────────────────────────

class MockLLMService(BaseLLMService):
    """Fallback LLM service used when no API keys are configured."""

    async def complete(self, messages: list[ChatMessage]) -> str:
        user_msg = next((m.content for m in reversed(messages) if m.role == "user"), "hello")
        return (
            f"I have received your message: '{user_msg}'. "
            "Your memories have been saved into the Memory Vault! "
            "To connect to live LLM models, please set your GEMINI_API_KEY in backend/.env or Settings."
        )

    async def stream(self, messages: list[ChatMessage]) -> AsyncGenerator[str, None]:
        response = await self.complete(messages)
        words = response.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.04)

    async def health_check(self) -> bool:
        return True


# ── Google Gemini ─────────────────────────────────────────────────────────────

class GeminiLLMService(BaseLLMService):
    def __init__(self) -> None:
        api_key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
        if not api_key:
            raise LLMError("GEMINI_API_KEY (or GOOGLE_API_KEY) is required for Gemini LLM.")
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model_name = settings.LLM_MODEL or "gemini-flash-latest"
        self._model = genai.GenerativeModel(model_name)

    async def complete(self, messages: list[ChatMessage]) -> str:
        prompt = "\n".join(f"{m.role}: {m.content}" for m in messages)
        try:
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, lambda: self._model.generate_content(prompt))
            return resp.text
        except Exception as e:
            logger.warning("Gemini completion fallback triggered", error=str(e))
            if "ResourceExhausted" in str(e) or "429" in str(e):
                return "Gemini API rate limit reached. Please wait a moment and try again."
            return f"Gemini response unavailable: {e}"

    async def stream(self, messages: list[ChatMessage]) -> AsyncGenerator[str, None]:
        prompt = "\n".join(f"{m.role}: {m.content}" for m in messages)
        loop = asyncio.get_event_loop()
        try:
            resp = await loop.run_in_executor(
                None, lambda: self._model.generate_content(prompt, stream=True)
            )
            for chunk in resp:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.warning("Gemini streaming fallback triggered", error=str(e))
            if "ResourceExhausted" in str(e) or "429" in str(e):
                yield "Gemini API rate limit reached. Please wait a moment and try again."
            else:
                yield f"[Gemini API Notice: {e}]"

    async def health_check(self) -> bool:
        return bool(settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY)


# ── OpenAI ────────────────────────────────────────────────────────────────────

class OpenAILLMService(BaseLLMService):
    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise LLMError("OPENAI_API_KEY is required for OpenAI LLM.")
        import openai
        self._client = openai.AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )

    async def complete(self, messages: list[ChatMessage]) -> str:
        try:
            resp = await self._client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[m.to_dict() for m in messages],
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                timeout=settings.LLM_TIMEOUT,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            raise LLMError(f"OpenAI completion failed: {e}") from e

    async def stream(self, messages: list[ChatMessage]) -> AsyncGenerator[str, None]:
        try:
            async with await self._client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[m.to_dict() for m in messages],
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                stream=True,
                timeout=settings.LLM_TIMEOUT,
            ) as stream_resp:
                async for chunk in stream_resp:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
        except Exception as e:
            raise LLMError(f"OpenAI streaming failed: {e}") from e

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False


# ── Anthropic Claude ──────────────────────────────────────────────────────────

class AnthropicLLMService(BaseLLMService):
    def __init__(self) -> None:
        if not settings.ANTHROPIC_API_KEY:
            raise LLMError("ANTHROPIC_API_KEY is required for Anthropic LLM.")
        import anthropic
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    def _split_messages(self, messages: list[ChatMessage]):
        system = " ".join(m.content for m in messages if m.role == "system")
        chat = [m.to_dict() for m in messages if m.role != "system"]
        return system, chat

    async def complete(self, messages: list[ChatMessage]) -> str:
        system, chat = self._split_messages(messages)
        try:
            resp = await self._client.messages.create(
                model=settings.LLM_MODEL,
                max_tokens=settings.LLM_MAX_TOKENS,
                system=system,
                messages=chat,
            )
            return resp.content[0].text
        except Exception as e:
            raise LLMError(f"Anthropic completion failed: {e}") from e

    async def stream(self, messages: list[ChatMessage]) -> AsyncGenerator[str, None]:
        system, chat = self._split_messages(messages)
        try:
            async with self._client.messages.stream(
                model=settings.LLM_MODEL,
                max_tokens=settings.LLM_MAX_TOKENS,
                system=system,
                messages=chat,
            ) as stream_resp:
                async for text in stream_resp.text_stream:
                    yield text
        except Exception as e:
            raise LLMError(f"Anthropic streaming failed: {e}") from e

    async def health_check(self) -> bool:
        return bool(settings.ANTHROPIC_API_KEY)


# ── Ollama (local) ────────────────────────────────────────────────────────────

class OllamaLLMService(BaseLLMService):
    def __init__(self) -> None:
        self._base_url = settings.OLLAMA_BASE_URL
        self._model = settings.LLM_MODEL or "llama3"

    async def complete(self, messages: list[ChatMessage]) -> str:
        import httpx
        payload = {
            "model": self._model,
            "messages": [m.to_dict() for m in messages],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            try:
                resp = await client.post(f"{self._base_url}/api/chat", json=payload)
                resp.raise_for_status()
                return resp.json()["message"]["content"]
            except Exception as e:
                raise LLMError(f"Ollama completion failed: {e}") from e

    async def stream(self, messages: list[ChatMessage]) -> AsyncGenerator[str, None]:
        import httpx, json as json_lib
        payload = {
            "model": self._model,
            "messages": [m.to_dict() for m in messages],
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            async with client.stream("POST", f"{self._base_url}/api/chat", json=payload) as resp:
                async for line in resp.aiter_lines():
                    if line:
                        data = json_lib.loads(line)
                        if not data.get("done", False):
                            yield data["message"]["content"]

    async def health_check(self) -> bool:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False


# ── Factory ───────────────────────────────────────────────────────────────────

_llm_instance: BaseLLMService | None = None


def get_llm_service() -> BaseLLMService:
    """Return the configured LLM service (singleton with mock fallback)."""
    global _llm_instance
    if _llm_instance is None:
        provider = settings.LLM_PROVIDER.lower()
        api_key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
        try:
            if provider in ("google", "gemini") and api_key:
                _llm_instance = GeminiLLMService()
            elif provider == "openai" and settings.OPENAI_API_KEY:
                _llm_instance = OpenAILLMService()
            elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
                _llm_instance = AnthropicLLMService()
            elif provider == "ollama":
                _llm_instance = OllamaLLMService()
            elif api_key:
                _llm_instance = GeminiLLMService()
            else:
                logger.info("No API key configured for LLM. Falling back to MockLLMService.")
                _llm_instance = MockLLMService()
        except Exception as e:
            logger.warning(f"Failed to initialize {provider} LLM service: {e}. Falling back to MockLLMService.")
            _llm_instance = MockLLMService()

    return _llm_instance
