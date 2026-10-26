"""Voz da assistente: edge-tts (neural, precisa de internet) ou pyttsx3 (offline)."""

from __future__ import annotations

import asyncio
import os
import tempfile
import threading
import time


class Speaker:
    def __init__(self, cfg: dict):
        t = cfg["tts"]
        self.engine = t["motor"]
        self.voice = t["voz_edge"]
        self.rate = t["velocidade"]
        self.pitch = t["tom"]
        self._stop = threading.Event()
        self._mixer_ready = False
        self._offline = None
        self._lock = threading.Lock()

    # -- API pública -------------------------------------------------------
    def speak(self, text: str) -> None:
        """Fala o texto e só volta quando terminar (ou for interrompida)."""
        text = text.strip()
        if not text:
            return
        self._stop.clear()
        if self.engine == "edge":
            try:
                self._speak_edge(text)
                return
            except Exception:  # noqa: BLE001 - sem internet etc.: cai para offline
                self.engine = "offline"
        self._speak_offline(text)

    def stop(self) -> None:
        self._stop.set()
        if self._mixer_ready:
            try:
                import pygame

                pygame.mixer.music.stop()
            except Exception:  # noqa: BLE001
                pass

    # -- edge-tts ----------------------------------------------------------
    def _ensure_mixer(self) -> None:
        if not self._mixer_ready:
            import pygame

            pygame.mixer.init()
            self._mixer_ready = True

    async def _synth(self, text: str, path: str) -> None:
        import edge_tts

        comm = edge_tts.Communicate(text, self.voice, rate=self.rate, pitch=self.pitch)
        await comm.save(path)

    def _speak_edge(self, text: str) -> None:
        import pygame

        self._ensure_mixer()
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        try:
            asyncio.run(self._synth(text, path))
            if self._stop.is_set():
                return
            with self._lock:
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()
            while pygame.mixer.music.get_busy() and not self._stop.is_set():
                time.sleep(0.03)
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    # -- offline -----------------------------------------------------------
    def _speak_offline(self, text: str) -> None:
        import pyttsx3

        if self._offline is None:
            self._offline = pyttsx3.init()
            for v in self._offline.getProperty("voices"):
                langs = " ".join(str(x) for x in getattr(v, "languages", []))
                if "pt" in langs.lower() or "portug" in v.name.lower() or "maria" in v.name.lower():
                    self._offline.setProperty("voice", v.id)
                    break
            self._offline.setProperty("rate", 185)
        self._offline.say(text)
        self._offline.runAndWait()
