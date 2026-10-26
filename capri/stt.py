"""Reconhecimento de voz local com faster-whisper."""

from __future__ import annotations

import numpy as np


class Transcriber:
    def __init__(self, cfg: dict):
        s = cfg["stt"]
        self.model_name = s["modelo"]
        self.language = s["idioma"]
        self.device_pref = s["dispositivo"]
        self._model = None
        self.device_in_use = ""

    def _load(self, device: str) -> None:
        from faster_whisper import WhisperModel

        compute = "float16" if device == "cuda" else "int8"
        self._model = WhisperModel(self.model_name, device=device, compute_type=compute)
        self.device_in_use = device

    def load(self) -> None:
        """Carrega o modelo. No modo auto, tenta GPU e cai para CPU se falhar."""
        if self._model is not None:
            return
        order = {"auto": ["cuda", "cpu"], "cuda": ["cuda"], "cpu": ["cpu"]}.get(
            self.device_pref, ["cpu"]
        )
        last: Exception | None = None
        for dev in order:
            try:
                self._load(dev)
                return
            except Exception as exc:  # noqa: BLE001
                last = exc
        raise RuntimeError(f"Não consegui carregar o Whisper: {last}")

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size < 1600:  # menos de 0,1 s
            return ""
        self.load()
        try:
            text = self._run(audio)
        except Exception:
            # Falta de cuDNN/cuBLAS costuma estourar só aqui. Refaz na CPU.
            if self.device_in_use == "cuda" and self.device_pref == "auto":
                self._model = None
                self._load("cpu")
                text = self._run(audio)
            else:
                raise
        return text

    def _run(self, audio: np.ndarray) -> str:
        segments, _ = self._model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()
