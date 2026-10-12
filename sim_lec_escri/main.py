"""Punto de entrada de SimOS Lab.

Uso:
    python main.py

Requiere haber activado el entorno virtual e instalado las dependencias
(ver README.md).
"""

from __future__ import annotations

import os
import sys


def _ensure_path() -> None:
    root = os.path.dirname(os.path.abspath(__file__))
    if root not in sys.path:
        sys.path.insert(0, root)


def main() -> None:
    _ensure_path()
    from src.ui.app import run

    run()


if __name__ == "__main__":
    main()
