"""Carrega as imagens do avatar (suas) ou gera um orbe genérico como substituto."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

# Estados que a janela usa. Cada um aceita uma imagem opcional em assets/.
STATES = ("idle", "listening", "thinking", "speaking", "speaking2")

_COLORS = {
    "idle": (120, 200, 255),
    "listening": (130, 255, 190),
    "thinking": (255, 215, 120),
    "speaking": (255, 140, 200),
    "speaking2": (255, 170, 220),
}


def placeholder(state: str, size: int = 300) -> Image.Image:
    """Orbe simples e original, só para a janela funcionar antes de você ter o avatar."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r, g, b = _COLORS.get(state, _COLORS["idle"])
    c = size // 2
    for i in range(10, 0, -1):  # brilho em camadas
        rad = int(size * 0.18 + i * size * 0.022)
        d.ellipse([c - rad, c - rad, c + rad, c + rad], fill=(r, g, b, 14 + (10 - i) * 5))
    core = int(size * 0.2 + (size * 0.03 if state == "speaking2" else 0))
    d.ellipse([c - core, c - core, c + core, c + core], fill=(r, g, b, 255))
    return img


def _fit(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    img = img.convert("RGBA")
    img.thumbnail((max_w, max_h), Image.LANCZOS)
    return img


def load_avatar(folder: Path, max_w: int, max_h: int) -> dict[str, Image.Image]:
    """Procura assets/<estado>.png. Estados sem arquivo usam o idle; sem idle, o orbe."""
    found: dict[str, Image.Image] = {}
    for state in STATES:
        for ext in (".png", ".webp", ".gif"):
            p = folder / f"{state}{ext}"
            if p.exists():
                found[state] = _fit(Image.open(p), max_w, max_h)
                break
    base = found.get("idle")
    out: dict[str, Image.Image] = {}
    for state in STATES:
        if state in found:
            out[state] = found[state]
        elif state == "speaking2":
            out[state] = found.get("speaking") or base or _fit(placeholder(state), max_w, max_h)
        elif base is not None:
            out[state] = base
        else:
            out[state] = _fit(placeholder(state), max_w, max_h)
    return out
