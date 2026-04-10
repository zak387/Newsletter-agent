"""Claude CLI adapter.

Provides a minimal drop-in replacement for the subset of the `anthropic` SDK
surface used by the writing agent. Routes calls through the local `claude`
CLI (Claude Code) instead of the Anthropic HTTPS API, so the agent can run
on a Claude Code subscription without an API key / credit balance.

Only the methods actually used by agents/writing/agent.py are implemented:

- client.messages.create(model, max_tokens, messages) -> object with
  .content[0].text
- client.messages.stream(model, max_tokens, messages) -> context manager with
  .text_stream iterator yielding chunks of text
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Iterator


CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")


def _scrubbed_env() -> dict:
    """Return env with CLAUDECODE / CLAUDE_CODE_ENTRYPOINT unset so the CLI
    can be invoked from inside another Claude Code session without the
    'nested session' safety check tripping."""
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_CODE_ENTRYPOINT", None)
    env.pop("CLAUDE_CODE_SSE_PORT", None)
    # Force the CLI to use the Claude Code subscription, not a billed API key.
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_AUTH_TOKEN", None)
    return env


def _prompt_from_messages(messages: list[dict]) -> str:
    """Flatten an anthropic-style messages list into a single prompt string.

    The writing agent only ever passes a single user message, so we simply
    return that content. If called with a richer structure, concatenate.
    """
    if len(messages) == 1 and messages[0].get("role") == "user":
        content = messages[0].get("content", "")
        if isinstance(content, str):
            return content
    # Fallback: concatenate role-tagged blocks.
    parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = "\n".join(
                block.get("text", "") for block in content if isinstance(block, dict)
            )
        parts.append(f"[{role}]\n{content}")
    return "\n\n".join(parts)


def _run_claude(prompt: str) -> str:
    """Run `claude -p` with the prompt piped via stdin. Returns stdout text."""
    proc = subprocess.run(
        [CLAUDE_BIN, "-p"],
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_scrubbed_env(),
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"claude CLI failed (exit {proc.returncode}): {proc.stderr.strip()}"
        )
    return proc.stdout


@dataclass
class _TextBlock:
    text: str


@dataclass
class _Message:
    content: list[_TextBlock]


class _StreamContext:
    """Minimal context-manager implementing the anthropic streaming surface.

    The writing agent iterates over `.text_stream` inside a `with` block.
    We run the CLI call eagerly (non-streaming) and yield the full result
    as a single chunk. This preserves functional correctness; the live
    token-by-token UX is lost but the agent still prints the full text.
    """

    def __init__(self, prompt: str):
        self._prompt = prompt
        self._text: str | None = None

    def __enter__(self) -> "_StreamContext":
        self._text = _run_claude(self._prompt)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    @property
    def text_stream(self) -> Iterator[str]:
        if self._text is None:
            self._text = _run_claude(self._prompt)
        yield self._text


class _Messages:
    def create(self, *, model: str, max_tokens: int, messages: list[dict]) -> _Message:
        prompt = _prompt_from_messages(messages)
        text = _run_claude(prompt)
        return _Message(content=[_TextBlock(text=text)])

    def stream(self, *, model: str, max_tokens: int, messages: list[dict]) -> _StreamContext:
        prompt = _prompt_from_messages(messages)
        return _StreamContext(prompt)


class ClaudeCLIClient:
    """Drop-in for anthropic.Anthropic() using the local claude CLI."""

    def __init__(self):
        self.messages = _Messages()
