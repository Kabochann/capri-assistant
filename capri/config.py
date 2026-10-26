"""Carregamento da configuração (config.toml) com valores padrão."""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib  # type: ignore

ROOT = Path(__file__).resolve().parent.parent

DEFAULTS: dict[str, Any] = {
    "assistente": {"nome": "Capri", "modo_escuta": "botao", "falar_respostas": True},
    "llm": {
        "url": "http://localhost:11434",
        "modelo": "qwen2.5:7b-instruct",
        "temperatura": 0.8,
        "num_ctx": 4096,
        "historico_max": 16,
    },
    "stt": {"modelo": "small", "idioma": "pt", "dispositivo": "auto"},
    "tts": {
        "motor": "edge",
        "voz_edge": "pt-BR-FranciscaNeural",
        "velocidade": "+5%",
        "tom": "+0Hz",
    },
    "audio": {
        "sample_rate": 16000,
        "limiar_voz": 0.012,
        "silencio_fim": 0.9,
        "max_gravacao": 15.0,
        "dispositivo_entrada": "",
    },
    "janela": {
        "largura": 360,
        "altura": 520,
        "sempre_no_topo": True,
        "pasta_avatar": "assets",
    },
    "acoes": {"habilitado": True, "apps": {}},
}


def _merge(base: dict, extra: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Lê o config.toml e completa o que faltar com os padrões."""
    cfg_path = Path(path) if path else ROOT / "config.toml"
    if not cfg_path.exists():
        return copy.deepcopy(DEFAULTS)
    with open(cfg_path, "rb") as fh:
        data = tomllib.load(fh)
    return _merge(DEFAULTS, data)


def resolve_path(value: str) -> Path:
    """Caminhos relativos no config são relativos à raiz do projeto."""
    p = Path(value)
    return p if p.is_absolute() else ROOT / p
