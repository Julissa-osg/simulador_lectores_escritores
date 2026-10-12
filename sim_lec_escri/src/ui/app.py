"""app.py — Ventana principal, navegación lateral y pantallas de inicio.

Contiene:
* :class:`MainWindow`: la ventana con la barra lateral y el área de contenido.
* :class:`DashboardView`: pantalla de bienvenida.
* :class:`IntroView`: introducción educativa con la analogía de la biblioteca.
* ``draw_winter_scene``: ilustración vectorial dibujada en el Canvas.

No hay ventana de glosario: el proyecto mantiene solo las pantallas esenciales
(Inicio, Introducción, Simulador, Comparar y Modo de estudio).
"""

from __future__ import annotations

import random
import tkinter as tk

import customtkinter as ctk

from . import theme
from .simulator_view import SimulatorView
from .comparison_view import ComparisonView
from .study_view import StudyView


def draw_winter_scene(canvas: tk.Canvas, w: int, h: int) -> None:
    """Ilustración vectorial discreta: paisaje invernal con pinos y nieve."""
    canvas.delete("all")
    canvas.configure(bg=theme.PAPER)
    # Luna
    canvas.create_oval(w - 90, 26, w - 40, 76, fill=theme.BEIGE, outline="")
    # Colinas
    canvas.create_oval(-40, h - 90, w * 0.6, h + 60, fill=theme.BLUE_LIGHT, outline="")
    canvas.create_oval(w * 0.4, h - 70, w + 60, h + 80, fill=theme.BLUE_MED, outline="")

    # Pinos
    def pine(x, base, size, color):
        canvas.create_rectangle(x - 3, base - 6, x + 3, base + 14, fill=theme.CHARCOAL, outline="")
        for i in range(3):
            top = base - size + i * (size / 3)
            spread = size * (0.38 + i * 0.16)
            canvas.create_polygon(
                x, top, x - spread, top + size * 0.55, x + spread, top + size * 0.55,
                fill=color, outline="",
            )

    pine(w * 0.22, h - 30, 70, theme.BLUE_DARK)
    pine(w * 0.33, h - 24, 52, theme.CHARCOAL)
    pine(w * 0.72, h - 28, 62, theme.BLUE_DARK)

    # Copos de nieve (semilla fija para que el dibujo sea estable)
    rng = random.Random(7)
    for _ in range(26):
        x = rng.randint(10, max(11, w - 10))
        y = rng.randint(10, max(11, h - 20))
        r = rng.choice([1, 1, 2])
        canvas.create_oval(x, y, x + r, y + r, fill=theme.PAPER, outline="")


class DashboardView(ctk.CTkFrame):
    """Pantalla de bienvenida."""

    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color=theme.BG, corner_radius=0)
        self.app = app

        wrapper = ctk.CTkFrame(self, fg_color="transparent")
        wrapper.pack(fill="both", expand=True, padx=48, pady=36)

        left = ctk.CTkFrame(wrapper, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            left, text="Bienvenido a SimOS Lab",
            font=theme.title_font(34), text_color=theme.CHARCOAL_DEEP,
        ).pack(anchor="w")
        ctk.CTkLabel(
            left, text="Simulador visual de concurrencia",
            font=theme.ui_font(16), text_color=theme.BLUE_DARK,
        ).pack(anchor="w", pady=(2, 18))

        card = ctk.CTkFrame(
            left, fg_color=theme.PAPER, corner_radius=14, border_width=1,
            border_color=theme.BEIGE,
        )
        card.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(
            card,
            text=(
                "Explora cómo varios lectores y escritores comparten un recurso, "
                "descubre los problemas que pueden aparecer y experimenta con "
                "diferentes mecanismos de sincronización."
            ),
            font=theme.ui_font(14), text_color=theme.TEXT, wraplength=560,
            justify="left",
        ).pack(anchor="w", padx=22, pady=20)

        for title, body in [
            ("Lectores", "Consultan el catálogo. Varios pueden leer a la vez."),
            ("Escritores", "Modifican el catálogo. Necesitan acceso exclusivo."),
            ("Recurso compartido", "El catálogo de la biblioteca, protegido o no."),
        ]:
            row = ctk.CTkFrame(left, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(
                row, text="•", font=theme.ui_font(16, "bold"),
                text_color=theme.BLUE_MED, width=18,
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=title + ": ", font=theme.ui_font(13, "bold"),
                text_color=theme.CHARCOAL,
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=body, font=theme.ui_font(13), text_color=theme.TEXT_SEC,
            ).pack(side="left")

        buttons = ctk.CTkFrame(left, fg_color="transparent")
        buttons.pack(fill="x", pady=(26, 0))
        ctk.CTkButton(
            buttons, text="Comenzar simulación", height=44, width=200,
            corner_radius=10, fg_color=theme.CHARCOAL, hover_color=theme.CHARCOAL_DEEP,
            font=theme.ui_font(14, "bold"), command=lambda: self.app.show("simulador"),
        ).pack(side="left")
        ctk.CTkButton(
            buttons, text="Guía de uso", height=44, width=150,
            corner_radius=10, fg_color=theme.BEIGE, hover_color=theme.STONE,
            text_color=theme.CHARCOAL, font=theme.ui_font(14, "bold"),
            command=lambda: self.app.show("intro"),
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            buttons, text="Modo de estudio", height=44, width=150,
            corner_radius=10, fg_color=theme.BEIGE, hover_color=theme.STONE,
            text_color=theme.CHARCOAL, font=theme.ui_font(14, "bold"),
            command=lambda: self.app.show("estudio"),
        ).pack(side="left")

        right = ctk.CTkFrame(wrapper, fg_color="transparent")
        right.pack(side="right", fill="both", padx=(24, 0))
        canvas = tk.Canvas(right, width=360, height=420, highlightthickness=0,
                           bg=theme.PAPER)
        canvas.pack()
        self.canvas = canvas
        canvas.bind("<Configure>", self._redraw)

    def _redraw(self, event=None) -> None:
        w = self.canvas.winfo_width() or 360
        h = self.canvas.winfo_height() or 420
        draw_winter_scene(self.canvas, w, h)


class IntroView(ctk.CTkFrame):
    """Introducción educativa con la analogía de la biblioteca."""

    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color=theme.BG, corner_radius=0)
        self.app = app

        ctk.CTkLabel(
            self, text="La biblioteca de SimOS Lab",
            font=theme.title_font(30), text_color=theme.CHARCOAL_DEEP,
        ).pack(anchor="w", padx=48, pady=(32, 4))
        ctk.CTkLabel(
            self,
            text=(
                "Imagina una biblioteca con un catálogo compartido. Varias personas "
                "pueden consultarlo a la vez, pero cuando alguien lo modifica hay que "
                "respetar reglas para evitar conflictos."
            ),
            font=theme.ui_font(14), text_color=theme.TEXT, wraplength=900,
            justify="left",
        ).pack(anchor="w", padx=48, pady=(0, 16))

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=48, pady=0)

        cards = [
            ("📖", "Lector", "Una persona que consulta el catálogo. No lo cambia, "
             "así que puede leer junto a otros lectores."),
            ("✎", "Escritor", "Una persona que modifica el catálogo. Mientras "
             "escribe, nadie más debe tocar el dato."),
            ("▤", "Recurso compartido", "El catálogo en sí. Es el dato que todos "
             "quieren leer o cambiar."),
            ("⚠", "Lo que puede fallar", "Si no se coordina el acceso, dos "
             "personas pueden pisarse y perder cambios. Puede haber esperas largas "
             "(inanición) o bloqueos mutuos (interbloqueo)."),
        ]
        for i, (icon, title, body) in enumerate(cards):
            card = ctk.CTkFrame(
                grid, fg_color=theme.PAPER, corner_radius=14, border_width=1,
                border_color=theme.BEIGE,
            )
            card.grid(row=i // 2, column=i % 2, padx=8, pady=8, sticky="nsew")
            grid.grid_columnconfigure(i % 2, weight=1)
            grid.grid_rowconfigure(i // 2, weight=1)
            ctk.CTkLabel(
                card, text=icon, font=theme.title_font(26), text_color=theme.BLUE_DARK,
            ).pack(anchor="w", padx=18, pady=(16, 0))
            ctk.CTkLabel(
                card, text=title, font=theme.ui_font(16, "bold"),
                text_color=theme.CHARCOAL,
            ).pack(anchor="w", padx=18, pady=(4, 2))
            ctk.CTkLabel(
                card, text=body, font=theme.ui_font(13), text_color=theme.TEXT_SEC,
                wraplength=380, justify="left",
            ).pack(anchor="w", padx=18, pady=(0, 16))

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=48, pady=18)
        ctk.CTkButton(
            bottom, text="Iniciar simulación", height=44, width=200,
            corner_radius=10, fg_color=theme.CHARCOAL, hover_color=theme.CHARCOAL_DEEP,
            font=theme.ui_font(14, "bold"), command=lambda: self.app.show("simulador"),
        ).pack(side="left")
        ctk.CTkLabel(
            bottom,
            text="   Cada pantalla responde:  ¿Qué pasa?  ·  ¿Por qué?  ·  ¿Solución?",
            font=theme.ui_font(12), text_color=theme.TEXT_SEC,
        ).pack(side="left")


# ==============================================================================
# Ventana principal y navegación
# ==============================================================================

NAV_ITEMS = [
    ("inicio", "Inicio", "⌂"),
    ("intro", "Introducción", "✎"),
    ("simulador", "Simulador", "▤"),
    ("comparar", "Comparar", "⊞"),
    ("estudio", "Modo de estudio", "?"),
]

VIEWS = {
    "inicio": DashboardView,
    "intro": IntroView,
    "simulador": SimulatorView,
    "comparar": ComparisonView,
    "estudio": StudyView,
}


class MainWindow(ctk.CTk):
    """Contenedor principal: barra lateral + área de contenido."""

    def __init__(self) -> None:
        super().__init__()
        theme.init_fonts()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("SimOS Lab · Simulador de Lectores y Escritores")
        self.geometry("1300x840")
        self.minsize(1120, 720)
        self.configure(fg_color=theme.BG)

        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._current_view = None
        self._current_name: str | None = None

        self._build_sidebar()

        self._content = ctk.CTkFrame(self, fg_color=theme.BG, corner_radius=0)
        self._content.pack(side="left", fill="both", expand=True)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.show("inicio")

    # ------------------------------------------------------------------
    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(
            self, width=232, corner_radius=0, fg_color=theme.PAPER,
            border_width=0,
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        header = ctk.CTkFrame(sidebar, fg_color="transparent")
        header.pack(fill="x", padx=22, pady=(26, 8))
        ctk.CTkLabel(
            header, text="SimOS Lab", font=theme.title_font(26),
            text_color=theme.CHARCOAL_DEEP,
        ).pack(anchor="w")
        ctk.CTkLabel(
            header, text="Simulador visual de concurrencia",
            font=theme.ui_font(12), text_color=theme.TEXT_SEC,
        ).pack(anchor="w", pady=(2, 0))

        ctk.CTkFrame(sidebar, height=1, fg_color=theme.BEIGE).pack(
            fill="x", padx=22, pady=(14, 14)
        )

        nav = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav.pack(fill="x", padx=12)
        for key, label, icon in NAV_ITEMS:
            btn = ctk.CTkButton(
                nav,
                text=f"  {icon}   {label}",
                anchor="w",
                height=40,
                corner_radius=10,
                font=theme.ui_font(13, "bold"),
                fg_color="transparent",
                hover_color=theme.BEIGE,
                text_color=theme.CHARCOAL,
                command=lambda k=key: self.show(k),
            )
            btn.pack(fill="x", pady=2)
            self._nav_buttons[key] = btn

        footer = ctk.CTkFrame(sidebar, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=22, pady=18)
        ctk.CTkLabel(
            footer, text="❄  Sistemas Operativos · 2026",
            font=theme.ui_font(11), text_color=theme.BLUE_MED,
        ).pack(anchor="w")

    # ------------------------------------------------------------------
    def show(self, name: str) -> None:
        if name == self._current_name:
            return
        if self._current_view is not None:
            self._current_view.destroy()
            self._current_view = None

        view_cls = VIEWS[name]
        self._current_view = view_cls(self._content, self)
        self._current_view.pack(fill="both", expand=True)
        self._current_name = name

        for key, btn in self._nav_buttons.items():
            if key == name:
                btn.configure(fg_color=theme.BLUE_LIGHT, text_color=theme.PAPER)
            else:
                btn.configure(fg_color="transparent", text_color=theme.CHARCOAL)

    def _on_close(self) -> None:
        if self._current_view is not None and hasattr(self._current_view, "on_close"):
            self._current_view.on_close()
        self.destroy()


def run() -> None:
    app = MainWindow()
    app.mainloop()