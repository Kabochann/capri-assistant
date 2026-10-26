"""Comandos simples que mexem no PC. Só roda o que está na lista do config.toml."""

from __future__ import annotations

import datetime as dt
import os
import re
import subprocess
import sys
import unicodedata
import webbrowser
from dataclasses import dataclass
from urllib.parse import quote_plus


@dataclass
class ActionResult:
    handled: bool
    reply: str = ""


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip(" .!?,")


_OPEN = re.compile(r"^(?:abr[ae]|abrir|inicia|iniciar|executa|executar)\s+(?:o |a |os |as )?(.+)$")
_SEARCH = re.compile(
    r"^(?:pesquis[ae]|pesquisar|busca|buscar|procura|procurar)\s+(?:por |sobre |no google |na internet )*(.+)$"
)
_TIME = re.compile(r"^(?:que horas sao|qual a hora|me diz as horas|horas)$")
_DATE = re.compile(r"^(?:que dia e hoje|qual a data|data de hoje|que data e hoje)$")

_DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
_MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


class Actions:
    def __init__(self, cfg: dict):
        self.enabled = bool(cfg["acoes"]["habilitado"])
        self.apps = {_norm(k): v for k, v in cfg["acoes"].get("apps", {}).items()}

    def handle(self, text: str) -> ActionResult:
        if not self.enabled:
            return ActionResult(False)
        t = _norm(text)

        if _TIME.match(t):
            now = dt.datetime.now()
            return ActionResult(True, f"Agora são {now.hour} horas e {now.minute} minutos.")

        if _DATE.match(t):
            now = dt.datetime.now()
            return ActionResult(
                True,
                f"Hoje é {_DIAS[now.weekday()]}, {now.day} de {_MESES[now.month - 1]} de {now.year}.",
            )

        m = _SEARCH.match(t)
        if m:
            # o termo vem do texto original para não perder acentos
            original = re.sub(r"\s+", " ", text.lower()).strip(" .!?,")
            m2 = _SEARCH.match(original)
            termo = m2.group(1) if m2 else m.group(1)
            webbrowser.open(f"https://www.google.com/search?q={quote_plus(termo)}")
            return ActionResult(True, f"Pronto, pesquisei {termo} pra você.")

        m = _OPEN.match(t)
        if m:
            alvo = m.group(1)
            cmd = self.apps.get(alvo)
            if cmd is None:
                return ActionResult(
                    True,
                    f"Não tenho {alvo} na minha lista de programas. "
                    "Você pode adicionar no arquivo config.toml.",
                )
            try:
                self._launch(cmd)
            except OSError:
                return ActionResult(True, f"Tentei abrir {alvo}, mas não consegui.")
            return ActionResult(True, f"Abrindo {alvo}.")

        return ActionResult(False)

    @staticmethod
    def _launch(cmd: str) -> None:
        if cmd.startswith(("http://", "https://")):
            webbrowser.open(cmd)
        elif sys.platform == "win32":
            os.startfile(cmd)  # type: ignore[attr-defined]  # noqa: S606
        else:
            subprocess.Popen([cmd])  # noqa: S603
