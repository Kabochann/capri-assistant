"""Captura do microfone com detecção simples de fim de fala (VAD por energia)."""

from __future__ import annotations

import threading
import time
from typing import Callable, Iterable

import numpy as np


class UtteranceDetector:
    """Recebe blocos de áudio e decide quando uma fala começou e terminou.

    Separado da captura para poder ser testado sem microfone.
    """

    def __init__(self, sample_rate: int, threshold: float, silence_s: float, max_s: float):
        self.sr = sample_rate
        self.threshold = threshold
        self.silence_s = silence_s
        self.max_s = max_s
        self.reset()

    def reset(self) -> None:
        self.chunks: list[np.ndarray] = []
        self.started = False
        self.silent_for = 0.0
        self.total = 0.0
        self.done = False

    @staticmethod
    def rms(block: np.ndarray) -> float:
        return float(np.sqrt(np.mean(np.square(block, dtype=np.float64)))) if block.size else 0.0

    def feed(self, block: np.ndarray) -> bool:
        """Retorna True quando a fala terminou."""
        dur = len(block) / self.sr
        loud = self.rms(block) >= self.threshold
        if not self.started:
            if loud:
                self.started = True
                self.chunks.append(block)
                self.total += dur
            return False
        self.chunks.append(block)
        self.total += dur
        self.silent_for = 0.0 if loud else self.silent_for + dur
        if self.silent_for >= self.silence_s or self.total >= self.max_s:
            self.done = True
        return self.done

    def audio(self) -> np.ndarray:
        if not self.chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(self.chunks).astype(np.float32)


class Microphone:
    def __init__(self, cfg: dict):
        a = cfg["audio"]
        self.sr = int(a["sample_rate"])
        self.threshold = float(a["limiar_voz"])
        self.silence_s = float(a["silencio_fim"])
        self.max_s = float(a["max_gravacao"])
        dev = a.get("dispositivo_entrada", "")
        self.device = dev if dev else None
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def listen_once(
        self,
        on_level: Callable[[float], None] | None = None,
        wait_timeout: float = 20.0,
    ) -> np.ndarray | None:
        """Bloqueia até uma fala completa. Retorna None se cancelado ou sem fala."""
        import sounddevice as sd  # import tardio: só precisa no PC do usuário

        self._cancel.clear()
        det = UtteranceDetector(self.sr, self.threshold, self.silence_s, self.max_s)
        block_size = int(self.sr * 0.05)
        t0 = time.monotonic()
        with sd.InputStream(
            samplerate=self.sr,
            channels=1,
            dtype="float32",
            blocksize=block_size,
            device=self.device,
        ) as stream:
            while not self._cancel.is_set():
                data, _ = stream.read(block_size)
                block = data[:, 0].copy()
                if on_level:
                    on_level(det.rms(block))
                if det.feed(block):
                    return det.audio()
                if not det.started and time.monotonic() - t0 > wait_timeout:
                    return None
        return None


def feed_all(det: UtteranceDetector, blocks: Iterable[np.ndarray]) -> np.ndarray | None:
    """Auxiliar para testes: alimenta vários blocos e devolve a fala, se houver."""
    for b in blocks:
        if det.feed(b):
            return det.audio()
    return None
