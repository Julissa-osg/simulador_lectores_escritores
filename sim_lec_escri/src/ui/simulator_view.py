"""Módulo 3: simulador principal.

La vista NO contiene lógica de simulación: solo lee ``engine.snapshot()`` y
dibuja. Los botones envían órdenes al :class:`SimulationController`.
"""

from __future__ import annotations

import tkinter as tk
import customtkinter as ctk

from . import theme
from ..engine import SimulationController, SimulationEngine
from ..scenarios import SCENARIO_GROUPS, find_variant


def round_rect(canvas: tk.Canvas, x1, y1, x2, y2, r=10, **kwargs):
    """Dibuja un rectangulo redondeado aproximado con un polígono suavizado."""
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
        x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class SimulatorCanvas(tk.Canvas):
    """Dibuja el estado del motor: hilos, recurso, colas y línea de tiempo."""

    def __init__(self, master) -> None:
        super().__init__(master, bg=theme.PAPER, highlightthickness=0)
        self.snapshot = None
        self.config_data = None
        self.mechanism = ""
        self.policy = ""
        self.bind("<Configure>", lambda e: self.redraw())

    def update_scene(self, snapshot, config, mechanism, policy) -> None:
        self.snapshot = snapshot
        self.config_data = config
        self.mechanism = mechanism
        self.policy = policy
        self.redraw()

    # ------------------------------------------------------------------
    def redraw(self) -> None:
        self.delete("all")
        w = self.winfo_width() or 800
        h = self.winfo_height() or 500
        if not self.snapshot:
            self.create_text(w / 2, h / 2, text="Inicia la simulación para ver el estado",
                             fill=theme.TEXT_SEC, font=theme.ui_font(14))
            return
        if self.snapshot.get("exclusive"):
            self._draw_deadlock(w, h)
        else:
            self._draw_readers_writers(w, h)
        self._draw_timeline(w, h)

    # ------------------------------------------------------------------
    def _draw_readers_writers(self, w: int, h: int) -> None:
        snap = self.snapshot
        margin = 18
        timeline_h = 54
        usable_h = h - timeline_h
        # Tamaños adaptativos para que la escena quepa aunque la ventana sea estrecha.
        cat_w = 210 if w >= 640 else int(max(120, w * 0.34))
        cat_h = 132
        gap = 26
        card_w = int(min(158, max(84, (w - cat_w - 2 * margin - 2 * gap) / 2)))
        card_h = 58
        cx = w / 2
        cat_x1, cat_y1 = cx - cat_w / 2, usable_h / 2 - cat_h / 2 - 10
        cat_x2, cat_y2 = cat_x1 + cat_w, cat_y1 + cat_h

        top = 30

        readers = [t for t in snap["threads"] if t["kind"] == "lector"]
        writers = [t for t in snap["threads"] if t["kind"] == "escritor"]
        active_r = set(snap["sync"]["active_readers"])
        active_w = set(snap["sync"]["active_writers"])
        waiting_ids = {x["tid"] for x in snap["sync"]["waiting"]}

        self._layout_column(readers, margin + 10, card_w, card_h, top,
                            usable_h - 30, active_r, waiting_ids, "left", cat_x1, cat_y1, cat_y2)
        self._layout_column(writers, w - margin - 10 - card_w, card_w, card_h, top,
                            usable_h - 30, active_w, waiting_ids, "right", cat_x2, cat_y1, cat_y2)

        self._draw_catalog(cat_x1, cat_y1, cat_x2, cat_y2, snap)
        self._draw_waiting_queue(cat_x1, cat_y2 + 14, cat_w, snap)

    def _layout_column(self, threads, x, cw, ch, top, bottom, active, waiting,
                       side, cat_x, cat_y1, cat_y2) -> None:
        if not threads:
            return
        n = len(threads)
        span = bottom - top
        step = span / max(n, 1)
        for i, t in enumerate(threads):
            y = top + step * i + (step - ch) / 2
            self._draw_thread_card(x, y, cw, ch, t, waiting)
            if t["tid"] in active:
                x_from = x + cw if side == "left" else x
                y_from = y + ch / 2
                y_to = (cat_y1 + cat_y2) / 2
                color = theme.SAGE if t["kind"] == "lector" else theme.BLUE_DARK
                self.create_line(x_from, y_from, cat_x, y_to, arrow="last",
                                 fill=color, width=2, smooth=True)

    def _draw_thread_card(self, x, y, w, h, t, waiting) -> None:
        state = t["state"]
        fill = theme.state_color(state)
        round_rect(self, x, y, x + w, y + h, 12, fill=fill, outline="")
        icon = "▤" if t["kind"] == "lector" else "✎"
        # Icono: libro abierto o lápiz
        self.create_text(x + 20, y + h / 2, text=icon, font=theme.title_font(16),
                         fill=theme.state_text_color(state))
        self.create_text(x + 38, y + 16, text=t["label"], anchor="w",
                         font=theme.ui_font(12, "bold"),
                         fill=theme.state_text_color(state))
        self.create_text(x + 38, y + 36, text=state, anchor="w",
                         font=theme.ui_font(11), fill=theme.state_text_color(state))
        if t.get("local_value") is not None and t["kind"] == "escritor":
            self.create_text(x + w - 12, y + h / 2, text=f"loc={t['local_value']}",
                             anchor="e", font=theme.mono_font(10),
                             fill=theme.state_text_color(state))

    def _draw_catalog(self, x1, y1, x2, y2, snap) -> None:
        active_w = snap["sync"]["active_writers"]
        active_r = snap["sync"]["active_readers"]
        if active_w:
            border = theme.RED
            label = "SECCIÓN CRÍTICA · ocupada"
        elif active_r:
            border = theme.SAGE
            label = "Lectura compartida"
        else:
            border = theme.BEIGE
            label = "Disponible"
        round_rect(self, x1, y1, x2, y2, 16, fill=theme.BG, outline=border, width=3)
        self.create_text((x1 + x2) / 2, y1 + 20, text="▤  Catálogo",
                         font=theme.ui_font(13, "bold"), fill=theme.CHARCOAL)
        res = snap["resource"]
        value_color = theme.CHARCOAL_DEEP if res["is_consistent"] else theme.RED
        self.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=str(res["value"]),
                         font=theme.mono_font(30, "bold"), fill=value_color)
        self.create_text((x1 + x2) / 2, y2 - 34, text=label,
                         font=theme.ui_font(10), fill=theme.TEXT_SEC)
        self.create_text((x1 + x2) / 2, y2 - 16,
                         text=f"esperado {res['expected_value']} · "
                              f"lectores {len(active_r)} · escritores {len(active_w)}",
                         font=theme.mono_font(9), fill=theme.TEXT_SEC)

    def _draw_waiting_queue(self, x, y, w, snap) -> None:
        waiting = snap["sync"]["waiting"]
        self.create_text(x, y, text="Cola de espera", anchor="nw",
                         font=theme.ui_font(10, "bold"), fill=theme.TEXT_SEC)
        if not waiting:
            self.create_text(x + w / 2, y + 22, text="(vacía)",
                             font=theme.ui_font(10), fill=theme.STONE)
            return
        labels = []
        for item in waiting:
            for t in snap["threads"]:
                if t["tid"] == item["tid"]:
                    labels.append(t["label"])
        self.create_text(x + w / 2, y + 22, text="  →  ".join(labels),
                         font=theme.mono_font(10), fill=theme.AMBER)

    # ------------------------------------------------------------------
    def _draw_deadlock(self, w: int, h: int) -> None:
        snap = self.snapshot
        timeline_h = 54
        usable_h = h - timeline_h
        threads = snap["threads"]
        resources = list(snap["exclusive"].values())

        tx = 80
        rx = w - 260
        self.create_text(w / 2, 22, text="Grafo de asignación de recursos",
                         font=theme.ui_font(13, "bold"), fill=theme.CHARCOAL)

        tpos = {}
        for i, t in enumerate(threads):
            y = 70 + i * 110
            tpos[t["tid"]] = y + 26
            self._draw_thread_card(tx, y, 170, 52, t, set())
        rpos = {}
        for i, r in enumerate(resources):
            y = 90 + i * 130
            rpos[r["rid"]] = y + 26
            fill = theme.RED if r["owner"] else theme.SAGE
            round_rect(self, rx, y, rx + 150, y + 52, 12, fill=fill, outline="")
            self.create_text(rx + 16, y + 18, text="▤ " + r["name"], anchor="w",
                             font=theme.ui_font(12, "bold"),
                             fill=theme.state_text_color("Bloqueado" if r["owner"] else "Ejecutando"))
            self.create_text(rx + 16, y + 36,
                             text="libre" if not r["owner"] else f"de {r['owner']}",
                             anchor="w", font=theme.ui_font(10),
                             fill=theme.state_text_color("Bloqueado" if r["owner"] else "Ejecutando"))

        # Flechas de asignación (recurso -> hilo) y de solicitud (hilo -> recurso)
        for r in resources:
            if r["owner"] and r["owner"] in tpos:
                self.create_line(rx + 150, rpos[r["rid"]], tx + 170, tpos[r["owner"]],
                                 arrow="last", fill=theme.SAGE, width=2)
            for waiter in r["waiting"]:
                if waiter in tpos:
                    self.create_line(tx + 170, tpos[waiter], rx, rpos[r["rid"]],
                                     arrow="last", fill=theme.RED, width=2, dash=(5, 3))

        if snap["deadlock"]:
            self.create_text(w / 2, usable_h - 24,
                             text="⚠ Interbloqueo: espera circular detectada",
                             font=theme.ui_font(13, "bold"), fill=theme.RED)

    # ------------------------------------------------------------------
    def _draw_timeline(self, w: int, h: int) -> None:
        snap = self.snapshot
        top = h - 46
        self.create_text(16, top - 12, text="Línea de tiempo (CPU)", anchor="w",
                         font=theme.ui_font(10, "bold"), fill=theme.TEXT_SEC)
        self.create_line(16, top, w - 16, top, fill=theme.BEIGE)
        timeline = snap["timeline"]
        max_cells = max(1, (w - 40) // 22)
        timeline = timeline[-max_cells:]
        ids = {t["tid"]: t for t in snap["threads"]}
        x = 16
        for _, tid in timeline:
            t = ids.get(tid, {})
            color = theme.BLUE_LIGHT if t.get("kind") == "lector" else theme.BLUE_DARK
            self.create_rectangle(x, top + 6, x + 18, top + 30, fill=color, outline="")
            self.create_text(x + 9, top + 18, text=tid[0], fill=theme.PAPER,
                             font=theme.mono_font(9, "bold"))
            x += 21


class SimulatorView(ctk.CTkFrame):
    """Módulo 3 completo: controles + escena + registro + explicaciones."""

    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color=theme.BG, corner_radius=0)
        self.app = app
        self._after_id = None
        self._show_explanations = True

        self.group = SCENARIO_GROUPS[0]
        self.config_data = self.group.variants[0].config
        self.engine = SimulationEngine(self.config_data)
        self.controller = SimulationController(self.engine)

        self._build_header()
        self._build_body()
        self._build_bottom()
        self._sync_variant_options()
        self._refresh_all()
        self._schedule()

    # ==================================================================
    # Construcción
    # ==================================================================
    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=theme.PAPER, corner_radius=0)
        header.pack(fill="x")
        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.pack(fill="x", padx=24, pady=(14, 12))

        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left")
        self.header_title = ctk.CTkLabel(
            left, text="", font=theme.title_font(20), text_color=theme.CHARCOAL_DEEP,
        )
        self.header_title.pack(anchor="w")
        self.header_sub = ctk.CTkLabel(
            left, text="", font=theme.ui_font(12), text_color=theme.TEXT_SEC,
        )
        self.header_sub.pack(anchor="w")

        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right")
        ctk.CTkLabel(right, text="Escenario", font=theme.ui_font(11, "bold"),
                     text_color=theme.TEXT_SEC).pack(anchor="w")
        self.group_menu = ctk.CTkOptionMenu(
            right, values=[g.title for g in SCENARIO_GROUPS], width=250, height=32,
            font=theme.ui_font(12), fg_color=theme.BEIGE, text_color=theme.CHARCOAL,
            button_color=theme.BLUE_MED, button_hover_color=theme.BLUE_DARK,
            dropdown_font=theme.ui_font(12), command=self._on_group_change,
        )
        self.group_menu.pack(pady=(2, 6))
        ctk.CTkLabel(right, text="Variante / mecanismo", font=theme.ui_font(11, "bold"),
                     text_color=theme.TEXT_SEC).pack(anchor="w")
        self.variant_menu = ctk.CTkOptionMenu(
            right, values=["—"], width=250, height=32, font=theme.ui_font(12),
            fg_color=theme.BEIGE, text_color=theme.CHARCOAL, button_color=theme.BLUE_MED,
            button_hover_color=theme.BLUE_DARK, dropdown_font=theme.ui_font(12),
            command=self._on_variant_change,
        )
        self.variant_menu.pack(pady=(2, 0))

        ctk.CTkFrame(self, height=1, fg_color=theme.BEIGE).pack(fill="x")

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color=theme.BG, corner_radius=0)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self.canvas = SimulatorCanvas(body)
        self.canvas.pack(side="left", fill="both", expand=True)

        panel = ctk.CTkFrame(body, fg_color=theme.PAPER, corner_radius=14,
                             border_width=1, border_color=theme.BEIGE, width=330)
        panel.pack(side="right", fill="y", padx=(12, 0))
        panel.pack_propagate(False)

        ctk.CTkLabel(panel, text="Controles", font=theme.ui_font(14, "bold"),
                     text_color=theme.CHARCOAL).pack(anchor="w", padx=18, pady=(16, 8))

        btns = ctk.CTkFrame(panel, fg_color="transparent")
        btns.pack(fill="x", padx=18)
        self.play_btn = self._button(btns, "Iniciar", self._on_play, theme.CHARCOAL)
        self.play_btn.grid(row=0, column=0, padx=(0, 6), pady=4, sticky="ew")
        self.step_btn = self._button(btns, "Un paso", self._on_step, theme.BLUE_MED)
        self.step_btn.grid(row=0, column=1, padx=(6, 0), pady=4, sticky="ew")
        self.reset_btn = self._button(btns, "Reiniciar", self._on_reset, theme.BEIGE,
                                      text_color=theme.CHARCOAL)
        self.reset_btn.grid(row=1, column=0, padx=(0, 6), pady=4, sticky="ew")
        self.pause_btn = self._button(btns, "Pausar", self._on_pause, theme.BEIGE,
                                      text_color=theme.CHARCOAL)
        self.pause_btn.grid(row=1, column=1, padx=(6, 0), pady=4, sticky="ew")
        btns.grid_columnconfigure(0, weight=1)
        btns.grid_columnconfigure(1, weight=1)

        speed_row = ctk.CTkFrame(panel, fg_color="transparent")
        speed_row.pack(fill="x", padx=18, pady=(10, 4))
        ctk.CTkLabel(speed_row, text="Velocidad", font=theme.ui_font(11, "bold"),
                     text_color=theme.TEXT_SEC).pack(anchor="w")
        self.speed_menu = ctk.CTkOptionMenu(
            speed_row, values=list(SimulationController.SPEEDS.keys()), width=280,
            height=30, font=theme.ui_font(12), fg_color=theme.BEIGE,
            text_color=theme.CHARCOAL, button_color=theme.BLUE_MED,
            button_hover_color=theme.BLUE_DARK, command=self._on_speed,
        )
        self.speed_menu.set("Normal")
        self.speed_menu.pack(pady=(2, 0))

        self.explain_check = ctk.CTkCheckBox(
            panel, text="Mostrar explicaciones", font=theme.ui_font(12),
            text_color=theme.TEXT, fg_color=theme.BLUE_MED,
            hover_color=theme.BLUE_DARK, command=self._on_toggle_explanations,
        )
        self.explain_check.select()
        self.explain_check.pack(anchor="w", padx=18, pady=(10, 6))

        ctk.CTkFrame(panel, height=1, fg_color=theme.BEIGE).pack(fill="x", padx=18, pady=6)
        ctk.CTkLabel(panel, text="Estado", font=theme.ui_font(14, "bold"),
                     text_color=theme.CHARCOAL).pack(anchor="w", padx=18, pady=(4, 4))

        self.status_box = ctk.CTkTextbox(
            panel, height=150, fg_color=theme.BG, text_color=theme.TEXT,
            font=theme.mono_font(11), corner_radius=10, border_width=0, wrap="word",
        )
        self.status_box.pack(fill="x", padx=18, pady=(0, 6))

        ctk.CTkFrame(panel, height=1, fg_color=theme.BEIGE).pack(fill="x", padx=18, pady=6)
        ctk.CTkLabel(panel, text="Puntos clave", font=theme.ui_font(14, "bold"),
                     text_color=theme.CHARCOAL).pack(anchor="w", padx=18, pady=(4, 4))
        self.teaching_box = ctk.CTkTextbox(
            panel, height=110, fg_color=theme.BG, text_color=theme.TEXT_SEC,
            font=theme.ui_font(11), corner_radius=10, border_width=0, wrap="word",
        )
        self.teaching_box.pack(fill="both", expand=True, padx=18, pady=(0, 16))

    def _build_bottom(self) -> None:
        self.bottom = ctk.CTkFrame(self, fg_color=theme.BG, corner_radius=0, height=236)
        self.bottom.pack(fill="x", padx=16, pady=(0, 14))
        self.bottom.pack_propagate(False)

        self.explain_card = ctk.CTkFrame(
            self.bottom, fg_color=theme.PAPER, corner_radius=14, border_width=1,
            border_color=theme.BEIGE, width=440,
        )
        self.explain_card.pack(side="left", fill="y")
        self.explain_card.pack_propagate(False)
        ctk.CTkLabel(self.explain_card, text="¿Qué está pasando?",
                     font=theme.ui_font(13, "bold"), text_color=theme.CHARCOAL,
                     ).pack(anchor="w", padx=16, pady=(12, 2))
        self.big_explain = ctk.CTkTextbox(
            self.explain_card, fg_color=theme.BG, text_color=theme.TEXT,
            font=theme.ui_font(12), wrap="word", corner_radius=10, border_width=0,
        )
        self.big_explain.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        log_card = ctk.CTkFrame(self.bottom, fg_color=theme.PAPER, corner_radius=14,
                                border_width=1, border_color=theme.BEIGE)
        log_card.pack(side="right", fill="both", expand=True, padx=(12, 0))

        log_head = ctk.CTkFrame(log_card, fg_color="transparent")
        log_head.pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(log_head, text="Registro de eventos", font=theme.ui_font(13, "bold"),
                     text_color=theme.CHARCOAL).pack(side="left")
        self.thread_filter = ctk.CTkOptionMenu(
            log_head, values=["Todos los hilos"], width=150, height=26,
            font=theme.ui_font(11), fg_color=theme.BEIGE, text_color=theme.CHARCOAL,
            button_color=theme.BLUE_MED, command=lambda _: self._refresh_log(),
        )
        self.thread_filter.pack(side="right")
        self.type_filter = ctk.CTkOptionMenu(
            log_head, values=["Todos los tipos"], width=170, height=26,
            font=theme.ui_font(11), fg_color=theme.BEIGE, text_color=theme.CHARCOAL,
            button_color=theme.BLUE_MED, command=lambda _: self._refresh_log(),
        )
        self.type_filter.pack(side="right", padx=8)

        self.log_box = ctk.CTkTextbox(
            log_card, fg_color=theme.BG, text_color=theme.TEXT,
            font=theme.mono_font(11), wrap="word", corner_radius=10, border_width=0,
        )
        self.log_box.pack(fill="both", expand=True, padx=14, pady=(0, 12))

    def _button(self, master, text, command, color, text_color=theme.PAPER):
        return ctk.CTkButton(
            master, text=text, command=command, height=38, corner_radius=10,
            font=theme.ui_font(12, "bold"), fg_color=color,
            hover_color=theme.CHARCOAL_DEEP if color == theme.CHARCOAL else theme.STONE,
            text_color=text_color,
        )

    # ==================================================================
    # Eventos de interfaz
    # ==================================================================
    def _on_group_change(self, title: str) -> None:
        for g in SCENARIO_GROUPS:
            if g.title == title:
                self.group = g
                break
        self._sync_variant_options()
        self._load_config(self.group.variants[0].config)

    def _sync_variant_options(self) -> None:
        labels = [v.label for v in self.group.variants]
        self.variant_menu.configure(values=labels)
        self.variant_menu.set(labels[0])

    def _on_variant_change(self, label: str) -> None:
        for v in self.group.variants:
            if v.label == label:
                self._load_config(v.config)
                return

    def _load_config(self, config) -> None:
        self.config_data = config
        self.engine = SimulationEngine(config)
        self.controller = SimulationController(self.engine, self.controller.speed_name)
        self._reset_filters()
        self._refresh_all()

    def _on_play(self) -> None:
        self.controller.play()
        self.play_btn.configure(text="En marcha…")

    def _on_pause(self) -> None:
        running = self.controller.running
        if running:
            self.controller.pause()
            self.pause_btn.configure(text="Reanudar")
            self.play_btn.configure(text="Iniciar")
        else:
            self.controller.play()
            self.pause_btn.configure(text="Pausar")

    def _on_step(self) -> None:
        self.controller.step_once()
        self.pause_btn.configure(text="Reanudar")
        self.play_btn.configure(text="Iniciar")
        self._refresh_all()

    def _on_reset(self) -> None:
        self.controller.reset()
        self.play_btn.configure(text="Iniciar")
        self.pause_btn.configure(text="Pausar")
        self._refresh_all()

    def _on_speed(self, name: str) -> None:
        self.controller.set_speed(name)

    def _on_toggle_explanations(self) -> None:
        self._show_explanations = bool(self.explain_check.get())
        self._refresh_explanations()

    # ==================================================================
    # Bucle de animación
    # ==================================================================
    def _schedule(self) -> None:
        self._after_id = self.after(self.controller.interval_ms, self._loop)

    def _loop(self) -> None:
        if self.controller.running:
            event = self.controller.tick()
            if event is not None:
                self._refresh_all()
            if self.engine.finished:
                self.controller.pause()
                self.play_btn.configure(text="Iniciar")
        self._schedule()

    def on_close(self) -> None:
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    # ==================================================================
    # Refresco de la vista
    # ==================================================================
    def _refresh_all(self) -> None:
        snap = self.engine.snapshot()
        self.header_title.configure(text=self.config_data.title)
        self.header_sub.configure(text=self.config_data.subtitle)
        self.canvas.update_scene(snap, self.config_data,
                                 self.config_data.sync_mechanism,
                                 self.config_data.sync_policy)
        self._refresh_status(snap)
        self._refresh_teaching()
        self._refresh_explanations()
        self._refresh_log()
        self._refresh_filters(snap)

    def _refresh_status(self, snap) -> None:
        lines = [
            f"mecanismo  : {snap['sync']['mechanism']}",
            f"política   : {snap['sync']['policy']}",
            f"evento     : {snap['event_count']}",
            f"recurso    : {snap['resource']['value']} "
            f"(esperado {snap['resource']['expected_value']})",
            f"consistente: {'sí' if snap['resource']['is_consistent'] else 'NO'}",
            f"lectores   : {len(snap['sync']['active_readers'])} activos",
            f"escritores : {len(snap['sync']['active_writers'])} activos",
            f"esperando  : {len(snap['sync']['waiting'])}",
            f"contextos  : {snap['context_switches']}",
        ]
        if snap["deadlock"]:
            lines.append("INTERBLOQUEO: sí ⚠")
        if snap.get("max_wait"):
            big = max(snap["max_wait"].items(), key=lambda kv: kv[1])
            if big[1] > 0:
                lines.append(f"mayor espera: {big[0]} ({big[1]})")
        self.status_box.configure(state="normal")
        self.status_box.delete("1.0", "end")
        self.status_box.insert("1.0", "\n".join(lines))
        self.status_box.configure(state="disabled")

    def _refresh_teaching(self) -> None:
        text = self.config_data.description + "\n\n"
        text += "\n".join("• " + p for p in self.config_data.teaching)
        self.teaching_box.configure(state="normal")
        self.teaching_box.delete("1.0", "end")
        self.teaching_box.insert("1.0", text)
        self.teaching_box.configure(state="disabled")

    def _refresh_explanations(self) -> None:
        """Rellena el panel «¿Qué está pasando?» con lo que ocurre en cada paso."""
        self.big_explain.configure(state="normal")
        self.big_explain.delete("1.0", "end")
        if self._show_explanations:
            cfg = self.config_data
            body = (
                f"Último paso: {self._last_event_text()}\n\n"
                f"¿Qué está pasando?\n{cfg.que_pasa}\n\n"
                f"¿Por qué?\n{cfg.por_que}\n\n"
                f"¿Solución?\n{cfg.solucion}"
            )
            self.big_explain.insert("1.0", body)
        self.big_explain.configure(state="disabled")

    def _last_event_text(self) -> str:
        last = self.engine.log.last
        if last is None:
            return "—"
        return last.short()

    def _reset_filters(self) -> None:
        self.thread_filter.configure(values=["Todos los hilos"])
        self.thread_filter.set("Todos los hilos")
        self.type_filter.configure(values=["Todos los tipos"])
        self.type_filter.set("Todos los tipos")

    def _refresh_filters(self, snap) -> None:
        threads = ["Todos los hilos"] + [t["label"] for t in snap["threads"]]
        current = self.thread_filter.get()
        self.thread_filter.configure(values=threads)
        if current not in threads:
            self.thread_filter.set("Todos los hilos")

        types = ["Todos los tipos"]
        for event in self.engine.log:
            if event.type.value not in types:
                types.append(event.type.value)
        current_t = self.type_filter.get()
        self.type_filter.configure(values=types)
        if current_t not in types:
            self.type_filter.set("Todos los tipos")

    def _refresh_log(self) -> None:
        thread_label = self.thread_filter.get()
        type_value = self.type_filter.get()
        tid = None
        if thread_label != "Todos los hilos":
            for t in self.engine.threads.values():
                if t.label == thread_label:
                    tid = t.label
                    break
        etype = None
        if type_value != "Todos los tipos":
            for event in self.engine.log:
                if event.type.value == type_value:
                    etype = event.type
                    break

        lines = []
        for event in self.engine.log:
            if tid is not None and event.thread != tid:
                continue
            if etype is not None and event.type is not etype:
                continue
            lines.append(event.short())
            for consequence in event.consequences:
                lines.append("      └ " + consequence)

        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.insert("1.0", "\n".join(lines))
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
