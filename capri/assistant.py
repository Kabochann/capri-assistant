"""Orquestra tudo: escuta -> transcreve -> pensa -> fala. Comunica com a janela por eventos."""

from __future__ import annotations

import queue
import threading
from typing import Callable, Iterable

from .actions import Actions
from .brain import Brain, BrainError

# Frases que o Whisper inventa quando só há ruído
_HALLUCINATIONS = {
    "legendas pela comunidade amara.org",
    "obrigado por assistir",
    "obrigada por assistir",
    "tchau tchau",
}

IDLE, LISTENING, THINKING, SPEAKING = "idle", "listening", "thinking", "speaking"


class Assistant:
    def __init__(self, cfg: dict, mic=None, stt=None, tts=None, brain=None, actions=None):
        self.cfg = cfg
        self.events: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self.brain = brain or Brain(cfg)
        self.actions = actions or Actions(cfg)
        self.speak_enabled = bool(cfg["assistente"]["falar_respostas"])
        self._mic = mic
        self._stt = stt
        self._tts = tts
        self._turn = threading.Lock()
        self._continuous = False
        self._interrupted = threading.Event()

    # -- componentes pesados (carregados sob demanda) ---------------------
    @property
    def mic(self):
        if self._mic is None:
            from .audio_in import Microphone

            self._mic = Microphone(self.cfg)
        return self._mic

    @property
    def stt(self):
        if self._stt is None:
            from .stt import Transcriber

            self._stt = Transcriber(self.cfg)
        return self._stt

    @property
    def tts(self):
        if self._tts is None:
            from .tts import Speaker

            self._tts = Speaker(self.cfg)
        return self._tts

    # -- eventos -----------------------------------------------------------
    def emit(self, kind: str, payload: object = None) -> None:
        self.events.put((kind, payload))

    def _status(self, value: str) -> None:
        self.emit("status", value)

    # -- inicialização -----------------------------------------------------
    def start(self) -> None:
        """Verificações iniciais em segundo plano (Ollama + modelo de voz)."""

        def boot() -> None:
            try:
                self.brain.check()
                self.emit("system", "Cérebro conectado.")
            except BrainError as exc:
                self.emit("error", str(exc))
            try:
                self.stt.load()
                self.emit("system", f"Ouvido pronto ({self.stt.device_in_use}).")
            except Exception as exc:  # noqa: BLE001
                self.emit("error", f"Voz de entrada indisponível: {exc}")
            if self.cfg["assistente"]["modo_escuta"] == "continuo":
                self.set_continuous(True)

        threading.Thread(target=boot, daemon=True).start()

    # -- entradas ----------------------------------------------------------
    def submit_text(self, text: str) -> None:
        text = text.strip()
        if text:
            threading.Thread(target=self._run_turn, args=(text,), daemon=True).start()

    def listen_once(self) -> None:
        threading.Thread(target=self._listen_turn, daemon=True).start()

    def set_continuous(self, on: bool) -> None:
        if on and not self._continuous:
            self._continuous = True
            threading.Thread(target=self._continuous_loop, daemon=True).start()
        elif not on:
            self._continuous = False
            try:
                self.mic.cancel()
            except Exception:  # noqa: BLE001
                pass
        self.emit("continuous", self._continuous)

    def interrupt(self) -> None:
        """Cala a Capri e para a geração atual."""
        self._interrupted.set()
        if self._tts is not None:
            self._tts.stop()

    def cancel_listening(self) -> None:
        if self._mic is not None:
            self._mic.cancel()

    # -- turnos ------------------------------------------------------------
    def _listen_turn(self) -> None:
        if not self._turn.acquire(blocking=False):
            self.emit("error", "Ainda estou ocupada com a resposta anterior.")
            return
        try:
            text = self._capture_and_transcribe()
        finally:
            self._turn.release()
        if text:
            self._run_turn(text)

    def _capture_and_transcribe(self) -> str:
        try:
            self._status(LISTENING)
            audio = self.mic.listen_once(on_level=lambda v: self.emit("level", v))
            if audio is None:
                self._status(IDLE)
                return ""
            self._status(THINKING)
            text = self.stt.transcribe(audio)
        except Exception as exc:  # noqa: BLE001
            self.emit("error", f"Falha ao ouvir: {exc}")
            self._status(IDLE)
            return ""
        if not text or text.lower().strip(" .!") in _HALLUCINATIONS:
            self._status(IDLE)
            return ""
        return text

    def _continuous_loop(self) -> None:
        while self._continuous:
            if not self._turn.acquire(blocking=False):
                self._sleep(0.2)
                continue
            try:
                text = self._capture_and_transcribe()
            finally:
                self._turn.release()
            if text and self._continuous:
                self._run_turn(text)

    @staticmethod
    def _sleep(seconds: float) -> None:
        threading.Event().wait(seconds)

    def _run_turn(self, text: str) -> None:
        if not self._turn.acquire(blocking=False):
            self.emit("error", "Ainda estou ocupada com a resposta anterior.")
            return
        self._interrupted.clear()
        try:
            self.emit("user", text)
            self._status(THINKING)
            result = self.actions.handle(text)
            if result.handled:
                self._deliver([result.reply])
            else:
                self._deliver(self.brain.stream_sentences(text))
        except BrainError as exc:
            self.emit("error", str(exc))
        except Exception as exc:  # noqa: BLE001
            self.emit("error", f"Algo deu errado: {exc}")
        finally:
            self._status(IDLE)
            self._turn.release()

    def _deliver(self, sentences: Iterable[str]) -> None:
        """Mostra e fala cada frase assim que ela fica pronta."""
        pending: "queue.Queue[str | None]" = queue.Queue()
        spoken: list[str] = []

        def player() -> None:
            while True:
                item = pending.get()
                if item is None:
                    return
                if self._interrupted.is_set() or not self.speak_enabled:
                    continue
                try:
                    self._status(SPEAKING)
                    self.tts.speak(item)
                except Exception as exc:  # noqa: BLE001
                    self.emit("error", f"Falha na voz: {exc}")
                    self.speak_enabled = False

        t = threading.Thread(target=player, daemon=True)
        t.start()
        try:
            for sentence in sentences:
                if self._interrupted.is_set():
                    break
                spoken.append(sentence)
                self.emit("assistant_partial", " ".join(spoken))
                pending.put(sentence)
        finally:
            pending.put(None)
            t.join()
        self.emit("assistant", " ".join(spoken))
