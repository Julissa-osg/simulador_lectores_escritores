"""Módulo 5: comparación de soluciones de sincronización.

Ejecuta el mismo escenario con cuatro enfoques y muestra sus métricas del
modelo (no del sistema operativo real).
"""

from __future__ import annotations

from dataclasses import replace

import customtkinter as ctk

from . import theme
from ..engine import SimulationEngine
from ..model import EventType
from ..scenarios import SCENARIO_GROUPS
from ..sync import MECH_MONITOR, MECH_NONE, MECH_SEMAPHORE, POLICY_FAIR, POLICY_READERS_FIRST

APPROACHES = [
    ("Sin sincronización", MECH_NONE, POLICY_READERS_FIRST),
    ("Semáforos", MECH_SEMAPHORE, POLICY_READERS_FIRST),
    ("Monitores", MECH_MONITOR, POLICY_READERS_FIRST),
    ("Acceso justo (FIFO)", MECH_SEMAPHORE, POLICY_FAIR),
]

METRICS = [
    ("Resultado del contador", "value"),
    ("Valor esperado", "expected"),
    ("Recurso consistente", "consistent"),
    ("Lectores atendidos", "readers"),
    ("Escritores atendidos", "writers"),
    ("Eventos ejecutados", "events"),
    ("Bloqueos", "blocks"),
    ("Mayor espera (eventos)", "max_wait"),
    ("Inanición detectada", "starvation"),
    ("Interbloqueo detectado", "deadlock"),
    ("Cambios de contexto", "context_switches"),
]


def run_metrics(config) -> dict:
    engine = SimulationEngine(config)
    blocks = 0
    readers = 0
    writers = 0
    while not engine.finished:
        event = engine.step()
        if event is None:
            break
        if event.type in (EventType.HILO_BLOQUEADO, EventType.RECURSO_SOLICITADO):
            blocks += 1
        elif event.type is EventType.LECTOR_ENTRA:
            readers += 1
        elif event.type is EventType.ESCRITOR_ENTRA:
            writers += 1
    max_wait = max(engine.max_wait.values()) if engine.max_wait else 0
    starvation = max_wait >= 15
    return {
        "value": engine.resource.value,
        "expected": engine.resource.expected_value,
        "consistent": "sí" if engine.resource.is_consistent else "NO",
        "readers": readers,
        "writers": writers,
        "events": engine.event_counter,
        "blocks": blocks,
        "max_wait": max_wait,
        "starvation": "sí" if starvation else "no",
        "deadlock": "sí" if engine.deadlock_detected else "no",
        "context_switches": engine.context_switches,
    }


class ComparisonView(ctk.CTkFrame):
    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color=theme.BG, corner_radius=0)
        self.app = app
        self.groups = [g for g in SCENARIO_GROUPS if g.key != "deadlock"]
        self.group = self.groups[0]

        ctk.CTkLabel(
            self, text="Comparación de soluciones", font=theme.title_font(30),
            text_color=theme.CHARCOAL_DEEP,
        ).pack(anchor="w", padx=40, pady=(28, 2))
        ctk.CTkLabel(
            self, text="Mismo escenario, cuatro enfoques. Las métricas son del modelo "
                      "educativo, no mediciones de un sistema operativo real.",
            font=theme.ui_font(13), text_color=theme.TEXT_SEC,
        ).pack(anchor="w", padx=40, pady=(0, 10))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=40, pady=(0, 10))
        ctk.CTkLabel(row, text="Escenario base:", font=theme.ui_font(12, "bold"),
                     text_color=theme.TEXT_SEC).pack(side="left", padx=(0, 8))
        self.menu = ctk.CTkOptionMenu(
            row, values=[g.title for g in self.groups], width=280, height=32,
            font=theme.ui_font(12), fg_color=theme.BEIGE, text_color=theme.CHARCOAL,
            button_color=theme.BLUE_MED, button_hover_color=theme.BLUE_DARK,
            command=self._on_change,
        )
        self.menu.pack(side="left")
        ctk.CTkButton(
            row, text="Recalcular", height=32, corner_radius=9, fg_color=theme.CHARCOAL,
            hover_color=theme.CHARCOAL_DEEP, font=theme.ui_font(12, "bold"),
            command=self._compute,
        ).pack(side="left", padx=10)

        self.table = ctk.CTkFrame(self, fg_color=theme.PAPER, corner_radius=14,
                                  border_width=1, border_color=theme.BEIGE)
        self.table.pack(fill="both", expand=True, padx=40, pady=(0, 20))

        note = (
            "Nota: «sin sincronización» no aplica exclusión mutua (los invariantes se "
            "relajan a propósito para mostrar la carrera). Un bloqueo en cola no es un "
            "interbloqueo; y la inanición se estima como una espera prolongada."
        )
        ctk.CTkLabel(self, text=note, font=theme.ui_font(11),
                     text_color=theme.TEXT_SEC, wraplength=1000,
                     justify="left").pack(anchor="w", padx=40, pady=(0, 16))

        self._compute()

    def _on_change(self, title: str) -> None:
        for g in self.groups:
            if g.title == title:
                self.group = g
                break
        self._compute()

    def _compute(self) -> None:
        for child in self.table.winfo_children():
            child.destroy()

        base = self.group.variants[0].config
        headers = ["Métrica"] + [a[0] for a in APPROACHES]
        results = []
        for _, mech, policy in APPROACHES:
            config = replace(base, sync_mechanism=mech, sync_policy=policy)
            results.append(run_metrics(config))

        for col, text in enumerate(headers):
            cell = ctk.CTkLabel(
                self.table, text=text, font=theme.ui_font(12, "bold"),
                text_color=theme.CHARCOAL if col == 0 else theme.BLUE_DARK,
                fg_color="transparent",
            )
            cell.grid(row=0, column=col, sticky="nsew", padx=8, pady=(14, 8))
            self.table.grid_columnconfigure(col, weight=1 if col == 0 else 1)

        for r, (label, key) in enumerate(METRICS, start=1):
            ctk.CTkLabel(
                self.table, text=label, font=theme.ui_font(12),
                text_color=theme.TEXT, anchor="w",
            ).grid(row=r, column=0, sticky="w", padx=12, pady=5)
            for c, metrics in enumerate(results, start=1):
                value = metrics[key]
                color = theme.TEXT
                if key == "consistent" and value == "NO":
                    color = theme.RED
                if key in ("starvation", "deadlock") and value == "sí":
                    color = theme.AMBER if key == "starvation" else theme.RED
                if key == "max_wait":
                    color = theme.AMBER if value >= 15 else theme.TEXT
                ctk.CTkLabel(
                    self.table, text=str(value), font=theme.mono_font(12),
                    text_color=color,
                ).grid(row=r, column=c, padx=8, pady=5)
