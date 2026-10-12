"""Identidad visual de SimOS Lab: diario invernal, papelería artesanal.

Todos los colores y tipografías viven aquí para que la interfaz tenga una sola
fuente de verdad. La paleta evita colores neón y reserva los colores de estado
(verde/ámbar/rojo) para cuando comunican algo importante.
"""

from __future__ import annotations

import tkinter.font as tkfont

# ---------------------------------------------------------------------------
# Paleta
# ---------------------------------------------------------------------------
BG = "#F5F1EF"            # blanco cálido (fondo principal)
PAPER = "#FFFCFA"         # papel blanco
BEIGE = "#E5DFDC"         # beige grisáceo
STONE = "#C9C7C6"         # gris piedra
BLUE_LIGHT = "#AEB7BE"    # gris azulado claro
BLUE_MED = "#929DA6"      # gris azulado medio
BLUE_DARK = "#606B75"     # gris azulado oscuro
CHARCOAL = "#414A53"      # carbón azulado
CHARCOAL_DEEP = "#30373E" # carbón profundo
TEXT = "#343A40"          # texto principal
TEXT_SEC = "#72777C"      # texto secundario
SAGE = "#879B8C"          # verde salvia (correcto)
AMBER = "#C5A777"         # ámbar suave (espera)
RED = "#B47777"           # rojo apagado (conflicto)

# Colores de estado de los hilos.
STATE_COLORS = {
    "Listo": BLUE_LIGHT,
    "Ejecutando": SAGE,
    "Esperando": AMBER,
    "Bloqueado": RED,
    "Terminado": STONE,
}
STATE_TEXT_COLORS = {
    "Listo": CHARCOAL_DEEP,
    "Ejecutando": PAPER,
    "Esperando": CHARCOAL_DEEP,
    "Bloqueado": PAPER,
    "Terminado": TEXT,
}

# ---------------------------------------------------------------------------
# Tipografia (con alternativas si el usuario no tiene la fuente)
# ---------------------------------------------------------------------------
_FAMILY_TITLE = "Georgia"
_FAMILY_UI = "DejaVu Sans"
_FAMILY_MONO = "DejaVu Sans Mono"
_initialized = False


def init_fonts() -> None:
    """Detecta las mejores fuentes disponibles en el sistema."""
    global _FAMILY_TITLE, _FAMILY_UI, _FAMILY_MONO, _initialized
    if _initialized:
        return
    families = set(tkfont.families())

    def pick(candidates: list[str], fallback: str) -> str:
        for name in candidates:
            if name in families:
                return name
        return fallback

    _FAMILY_TITLE = pick(
        ["Georgia", "DejaVu Serif", "Liberation Serif", "FreeSerif", "Times New Roman"],
        "DejaVu Serif",
    )
    _FAMILY_UI = pick(
        ["Inter", "Segoe UI", "DejaVu Sans", "Liberation Sans", "Helvetica", "Arial"],
        "DejaVu Sans",
    )
    _FAMILY_MONO = pick(
        ["JetBrains Mono", "Fira Code", "Cascadia Code", "DejaVu Sans Mono", "Consolas"],
        "DejaVu Sans Mono",
    )
    _initialized = True


def title_font(size: int = 22, weight: str = "bold") -> tuple:
    return (_FAMILY_TITLE, size, weight)


def ui_font(size: int = 13, weight: str = "normal") -> tuple:
    return (_FAMILY_UI, size, weight)


def mono_font(size: int = 12, weight: str = "normal") -> tuple:
    return (_FAMILY_MONO, size, weight)


def state_color(state: str) -> str:
    return STATE_COLORS.get(state, BLUE_LIGHT)


def state_text_color(state: str) -> str:
    return STATE_TEXT_COLORS.get(state, CHARCOAL_DEEP)
