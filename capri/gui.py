"""Janela flutuante com avatar, legenda e campo de texto (tkinter)."""

from __future__ import annotations

import queue
import tkinter as tk
from tkinter import scrolledtext

from PIL import ImageTk

from .assistant import IDLE, LISTENING, SPEAKING, THINKING, Assistant
from .avatar import load_avatar
from .config import resolve_path

TRANSPARENT = "#010203"  # cor-chave que o Windows deixa transparente
BG = "#14151c"
FG = "#e8e8f0"
ACCENT = "#ff8cc8"


class CapriWindow:
    def __init__(self, cfg: dict, assistant: Assistant):
        self.cfg = cfg
        self.bot = assistant
        w = int(cfg["janela"]["largura"])
        h = int(cfg["janela"]["altura"])
        self.root = tk.Tk()
        self.root.title(cfg["assistente"]["nome"])
        self.root.geometry(f"{w}x{h}+80+80")
        self.root.configure(bg=TRANSPARENT)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", bool(cfg["janela"]["sempre_no_topo"]))
        try:
            self.root.attributes("-transparentcolor", TRANSPARENT)  # só no Windows
        except tk.TclError:
            self.root.configure(bg=BG)

        folder = resolve_path(cfg["janela"]["pasta_avatar"])
        self.frames = {
            k: ImageTk.PhotoImage(v) for k, v in load_avatar(folder, w - 20, int(h * 0.5)).items()
        }
        self.state = IDLE
        self._mouth_open = False
        self._level = 0.0

        self.avatar = tk.Label(self.root, image=self.frames["idle"], bg=TRANSPARENT, bd=0)
        self.avatar.pack(pady=(8, 0))

        self.caption = tk.Label(
            self.root, text="", wraplength=w - 40, justify="center",
            bg=BG, fg=FG, font=("Segoe UI", 11), padx=10, pady=8,
        )
        self.caption.pack(fill="x", padx=14, pady=(6, 4))

        self.log = scrolledtext.ScrolledText(
            self.root, height=6, bg=BG, fg=FG, bd=0, wrap="word",
            font=("Segoe UI", 9), state="disabled",
        )
        self.log.tag_config("user", foreground="#9bd0ff")
        self.log.tag_config("bot", foreground=ACCENT)
        self.log.tag_config("sys", foreground="#888a99")
        self.log.tag_config("err", foreground="#ff7b7b")
        self.log.pack(fill="both", expand=True, padx=14)

        bar = tk.Frame(self.root, bg=BG)
        bar.pack(fill="x", padx=14, pady=(6, 10))
        self.entry = tk.Entry(bar, bg="#22232e", fg=FG, insertbackground=FG, bd=0,
                              font=("Segoe UI", 10))
        self.entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 6))
        self.entry.bind("<Return>", self._send)
        self.mic_btn = self._btn(bar, "🎤", self._on_mic)
        self.cont_btn = self._btn(bar, "∞", self._on_continuous)
        self.stop_btn = self._btn(bar, "■", lambda: self.bot.interrupt())
        self.close_btn = self._btn(bar, "✕", self.root.destroy)

        # arrastar a janela por qualquer lugar livre
        for widget in (self.root, self.avatar, self.caption):
            widget.bind("<ButtonPress-1>", self._drag_start)
            widget.bind("<B1-Motion>", self._drag_move)

        self._continuous = False
        self.root.after(50, self._poll)
        self.root.after(140, self._animate)

    # -- widgets -----------------------------------------------------------
    @staticmethod
    def _btn(parent, text, cmd):
        b = tk.Button(parent, text=text, command=cmd, bg="#2b2c3a", fg=FG, bd=0,
                      activebackground=ACCENT, width=3, font=("Segoe UI", 10))
        b.pack(side="left", padx=2)
        return b

    def _log(self, text: str, tag: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n", tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    # -- ações -------------------------------------------------------------
    def _send(self, _event=None) -> None:
        text = self.entry.get().strip()
        if text:
            self.entry.delete(0, "end")
            self.bot.submit_text(text)

    def _on_mic(self) -> None:
        if self.state == LISTENING:
            self.bot.cancel_listening()
        else:
            self.bot.listen_once()

    def _on_continuous(self) -> None:
        self.bot.set_continuous(not self._continuous)

    def _drag_start(self, e) -> None:
        self._dx, self._dy = e.x, e.y

    def _drag_move(self, e) -> None:
        x = self.root.winfo_x() + e.x - self._dx
        y = self.root.winfo_y() + e.y - self._dy
        self.root.geometry(f"+{x}+{y}")

    # -- loop de eventos ---------------------------------------------------
    def _poll(self) -> None:
        name = self.cfg["assistente"]["nome"]
        try:
            while True:
                kind, payload = self.bot.events.get_nowait()
                if kind == "status":
                    self.state = str(payload)
                    self._show_state()
                elif kind == "user":
                    self._log(f"Você: {payload}", "user")
                    self.caption.config(text="")
                elif kind == "assistant_partial":
                    self.caption.config(text=str(payload))
                elif kind == "assistant":
                    self._log(f"{name}: {payload}", "bot")
                elif kind == "system":
                    self._log(str(payload), "sys")
                elif kind == "error":
                    self._log(f"⚠ {payload}", "err")
                elif kind == "continuous":
                    self._continuous = bool(payload)
                    self.cont_btn.config(bg=ACCENT if self._continuous else "#2b2c3a")
                elif kind == "level":
                    self._level = float(payload)
        except queue.Empty:
            pass
        self.root.after(50, self._poll)

    def _show_state(self) -> None:
        self.mic_btn.config(bg=ACCENT if self.state == LISTENING else "#2b2c3a")
        key = {LISTENING: "listening", THINKING: "thinking", SPEAKING: "speaking"}.get(
            self.state, "idle"
        )
        self.avatar.config(image=self.frames[key])

    def _animate(self) -> None:
        """Alterna dois quadros enquanto ela fala (boquinha simples)."""
        if self.state == SPEAKING:
            self._mouth_open = not self._mouth_open
            self.avatar.config(image=self.frames["speaking2" if self._mouth_open else "speaking"])
        self.root.after(140, self._animate)

    def run(self) -> None:
        self.bot.start()
        self.root.mainloop()
