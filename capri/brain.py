"""Cérebro: conversa com o modelo local via Ollama (streaming)."""

from __future__ import annotations

import json
import re
from typing import Iterator

import requests

from .persona import build_system_prompt

_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+|\n+")


class BrainError(RuntimeError):
    pass


def split_sentences(buffer: str) -> tuple[list[str], str]:
    """Separa frases completas do buffer. Retorna (frases, resto_incompleto)."""
    parts = _SENTENCE_END.split(buffer)
    if len(parts) <= 1:
        return [], buffer
    done = [p.strip() for p in parts[:-1] if p.strip()]
    return done, parts[-1]


def clean_for_speech(text: str) -> str:
    """Remove markdown e emojis que atrapalham a voz."""
    text = re.sub(r"[*_`#>~]+", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(
        "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF]", "", text
    )
    return re.sub(r"\s+", " ", text).strip()


class Brain:
    def __init__(self, cfg: dict):
        self.llm = cfg["llm"]
        self.nome = cfg["assistente"]["nome"]
        self.history: list[dict] = []
        self._system = {"role": "system", "content": build_system_prompt(self.nome)}

    # -- histórico ---------------------------------------------------------
    def _trim(self) -> None:
        limit = int(self.llm["historico_max"])
        if len(self.history) > limit:
            self.history = self.history[-limit:]
            # nunca começar o histórico por uma resposta da assistente
            while self.history and self.history[0]["role"] != "user":
                self.history.pop(0)

    def reset(self) -> None:
        self.history.clear()

    # -- conexão -----------------------------------------------------------
    def check(self) -> None:
        """Confere se o Ollama está no ar e se o modelo foi baixado."""
        url = self.llm["url"].rstrip("/")
        try:
            r = requests.get(f"{url}/api/tags", timeout=4)
            r.raise_for_status()
        except requests.RequestException as exc:
            raise BrainError(
                "Não consegui falar com o Ollama. Ele está instalado e aberto? "
                "(https://ollama.com/download)"
            ) from exc
        names = {m.get("name", "") for m in r.json().get("models", [])}
        wanted = self.llm["modelo"]
        if wanted not in names and f"{wanted}:latest" not in names:
            raise BrainError(
                f"Modelo '{wanted}' não encontrado. Rode no terminal: ollama pull {wanted}"
            )

    # -- conversa ----------------------------------------------------------
    def stream_reply(self, user_text: str) -> Iterator[str]:
        """Gera a resposta em pedaços de texto (tokens)."""
        self.history.append({"role": "user", "content": user_text})
        self._trim()
        payload = {
            "model": self.llm["modelo"],
            "messages": [self._system, *self.history],
            "stream": True,
            "options": {
                "temperature": float(self.llm["temperatura"]),
                "num_ctx": int(self.llm["num_ctx"]),
            },
        }
        url = self.llm["url"].rstrip("/") + "/api/chat"
        full: list[str] = []
        try:
            with requests.post(url, json=payload, stream=True, timeout=120) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        full.append(chunk)
                        yield chunk
                    if data.get("done"):
                        break
        except requests.RequestException as exc:
            self.history.pop()  # descarta a pergunta que falhou
            raise BrainError(f"Erro ao falar com o modelo: {exc}") from exc
        self.history.append({"role": "assistant", "content": "".join(full)})

    def stream_sentences(self, user_text: str) -> Iterator[str]:
        """Gera a resposta frase por frase, pronta para ser falada."""
        buffer = ""
        for chunk in self.stream_reply(user_text):
            buffer += chunk
            sentences, buffer = split_sentences(buffer)
            for s in sentences:
                s = clean_for_speech(s)
                if s:
                    yield s
        tail = clean_for_speech(buffer)
        if tail:
            yield tail
