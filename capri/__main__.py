"""Ponto de entrada: python -m capri  (use --texto para modo terminal sem janela)."""

from __future__ import annotations

import argparse
import os

from .assistant import Assistant
from .config import ROOT, load_config


def run_terminal(cfg: dict) -> None:
    """Modo texto no terminal: útil para testar o cérebro e a voz sem a janela."""
    bot = Assistant(cfg)
    try:
        bot.brain.check()
    except Exception as exc:  # noqa: BLE001
        print(f"[erro] {exc}")
        return
    nome = cfg["assistente"]["nome"]
    print(f"{nome} no terminal. Digite 'sair' para encerrar.\n")
    while True:
        try:
            text = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in {"sair", "exit", "quit"}:
            break
        if not text:
            continue
        result = bot.actions.handle(text)
        if result.handled:
            print(f"{nome}: {result.reply}")
            bot._deliver([result.reply])  # noqa: SLF001
        else:
            parts: list[str] = []
            for s in bot.brain.stream_sentences(text):
                parts.append(s)
            reply = " ".join(parts)
            print(f"{nome}: {reply}")
            bot._deliver(parts)  # noqa: SLF001
        while not bot.events.empty():
            kind, payload = bot.events.get_nowait()
            if kind == "error":
                print(f"[aviso] {payload}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="capri")
    parser.add_argument("--config", help="caminho de um config.toml alternativo")
    parser.add_argument("--texto", action="store_true", help="modo terminal, sem janela")
    args = parser.parse_args()

    # O modelo de voz (Whisper) é baixado para dentro da pasta do projeto, e não para
    # C:\Users\...\.cache. Assim tudo fica no disco onde você instalou a Capri.
    os.environ.setdefault("HF_HOME", str(ROOT / "models" / "huggingface"))

    cfg = load_config(args.config)

    if args.texto:
        run_terminal(cfg)
        return

    from .gui import CapriWindow

    CapriWindow(cfg, Assistant(cfg)).run()


if __name__ == "__main__":
    main()
