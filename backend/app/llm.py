"""LLM clients. All stream text so the UI can show the answer as it's written."""
from __future__ import annotations

import re
from typing import Iterator, Protocol, Sequence

from .config import Settings


class LLM(Protocol):
    name: str

    def stream(self, system: str, messages: Sequence[dict], max_tokens: int) -> Iterator[str]: ...


class AnthropicLLM:
    def __init__(self, api_key: str, model: str):
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.name = f"anthropic:{model}"

    def stream(self, system: str, messages: Sequence[dict], max_tokens: int) -> Iterator[str]:
        with self.client.messages.stream(model=self.model, max_tokens=max_tokens, system=system,
                                         messages=list(messages), temperature=0) as s:
            yield from s.text_stream


class OpenAILLM:
    def __init__(self, api_key: str, model: str):
        import openai

        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.name = f"openai:{model}"

    def stream(self, system: str, messages: Sequence[dict], max_tokens: int) -> Iterator[str]:
        response = self.client.chat.completions.create(
            model=self.model, max_tokens=max_tokens, temperature=0, stream=True,
            messages=[{"role": "system", "content": system}, *messages])
        for part in response:
            if part.choices and part.choices[0].delta and part.choices[0].delta.content:
                yield part.choices[0].delta.content


class ExtractiveLLM:
    """Offline stand-in for tests and demos without an API key: quotes the first sentences of source [1].
    It doesn't generate anything, so it shows the pipeline working, not answer quality."""

    name = "extractive (offline)"
    _SOURCE = re.compile(r"\[1\] [^\n]*\n(.+?)(?:\n\n\[2\]|\n</sources>)", re.S)

    def stream(self, system: str, messages: Sequence[dict], max_tokens: int) -> Iterator[str]:
        m = self._SOURCE.search(messages[-1]["content"])
        if not m:
            yield "I couldn't find that in your documents."
            return
        sentences = re.split(r"(?<=[.!?])\s+", " ".join(m.group(1).split()))
        answer = " ".join(sentences[:2]).strip()
        for word in (answer + " [1]").split(" "):
            yield word + " "


def make_llm(settings: Settings) -> LLM:
    if settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        return AnthropicLLM(settings.anthropic_api_key, settings.anthropic_model)
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        return OpenAILLM(settings.openai_api_key, settings.openai_chat_model)
    if settings.llm_provider == "extractive":
        return ExtractiveLLM()
    raise RuntimeError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")
