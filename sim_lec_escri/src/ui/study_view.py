"""Módulo: modo de estudio con preguntas y respuestas explicadas.

Las preguntas viven aquí mismo (no hay un módulo educativo separado) porque
son contenido de esta pantalla.
"""

from __future__ import annotations

from dataclasses import dataclass

import customtkinter as ctk

from . import theme


@dataclass(frozen=True)
class Question:
    key: str
    text: str
    options: list[str]
    correct: int
    explanation: str
    topic: str


QUESTIONS: list[Question] = [
    Question(
        "q1",
        "¿Por qué dos escritores pueden perder una actualización?",
        [
            "Porque la CPU es demasiado lenta.",
            "Porque ambos leen el mismo valor antes de escribir.",
            "Porque el semáforo está roto.",
        ],
        1,
        "Cada escritor copia el valor (100) antes de que el otro escriba. "
        "Calculan 101 por separado y ambos escriben 101, así que un incremento "
        "se pierde. El resultado depende de la intercalación, no de la velocidad.",
        "race",
    ),
    Question(
        "q2",
        "¿Cuál es la diferencia entre bloqueo e interbloqueo?",
        [
            "Ninguna: son sinónimos.",
            "El bloqueo se resuelve solo; el interbloqueo es una espera circular "
            "que no termina sin intervención.",
            "El bloqueo solo ocurre en la CPU.",
        ],
        1,
        "Un bloqueo normal espera algo que llegará (por ejemplo, que un escritor "
        "libere). Un interbloqueo es una espera circular: cada hilo espera un "
        "recurso que retiene otro, y ninguno puede avanzar.",
        "deadlock",
    ),
    Question(
        "q3",
        "¿Por qué varios lectores pueden acceder simultáneamente?",
        [
            "Porque leer no modifica el dato, así que no hay conflicto entre ellos.",
            "Porque cada lector tiene su propia copia del catálogo.",
            "Porque el planificador lo permite siempre.",
        ],
        0,
        "Leer no cambia el valor compartido. Como los lectores no se afectan "
        "entre sí, pueden coincidir. En cambio, escribir sí modifica el dato y "
        "exige acceso exclusivo.",
        "readers",
    ),
    Question(
        "q4",
        "¿Qué función cumple un semáforo?",
        [
            "Guardar datos de forma permanente.",
            "Contar permisos y bloquear a quien hace wait cuando el valor es cero.",
            "Detectar interbloqueos automáticamente.",
        ],
        1,
        "Un semáforo es un contador con operaciones atómicas wait y signal. Si "
        "el valor es cero, wait bloquea al hilo hasta que otro haga signal. Según "
        "su valor inicial puede ser binario (mutex) o contador.",
        "sync",
    ),
    Question(
        "q5",
        "¿Cómo puede un escritor sufrir inanición?",
        [
            "Si los lectores llegan continuamente y la política los admite antes "
            "que al escritor.",
            "Si el contador de lectores se vuelve negativo.",
            "Si nunca pide el recurso.",
        ],
        0,
        "Con la política de prioridad a lectores, cada lector nuevo entra aunque "
        "haya un escritor esperando. Si los lectores no paran de llegar, el "
        "escritor no progresa: eso es inanición. Una cola FIFO justa lo evita.",
        "starvation",
    ),
    Question(
        "q6",
        "¿Por qué un cambio de contexto no soluciona una condición de carrera?",
        [
            "Porque los cambios de contexto son muy caros.",
            "Porque cambiar de hilo reparte la CPU, pero no impide que dos hilos "
            "accedan al dato a la vez.",
            "Porque el planificador no puede cambiar de hilo.",
        ],
        1,
        "El cambio de contexto decide quién usa la CPU, pero no protege el dato "
        "compartido. Para evitar carreras hace falta sincronización (exclusión "
        "mutua), que es un mecanismo distinto.",
        "context",
    ),
    Question(
        "q7",
        "¿Qué diferencia hay entre un monitor y un semáforo?",
        [
            "El monitor no sirve para sincronizar.",
            "El monitor encapsula el candado y usa variables de condición; el "
            "semáforo expone wait/signal como operaciones sueltas.",
            "Son exactamente lo mismo con otro nombre.",
        ],
        1,
        "El semáforo es una primitiva de bajo nivel que el programador debe usar "
        "con cuidado. El monitor agrupa el estado protegido y las condiciones, "
        "garantizando la exclusión mutua dentro del propio monitor. Su "
        "comportamiento puede ser equivalente, pero la abstracción es distinta.",
        "sync",
    ),
    Question(
        "q8",
        "¿Qué es una variable de condición?",
        [
            "Una variable que cambia con el tiempo.",
            "Un objeto que permite esperar hasta que se cumpla una condición.",
            "Un tipo especial de semáforo binario.",
        ],
        1,
        "Permite a un hilo suspender su ejecución hasta que otro señalice que la "
        "condición puede cumplirse. Al reanudar hay que volver a comprobar la "
        "condición en un bucle while, porque el estado pudo cambiar.",
        "sync",
    ),
    Question(
        "q9",
        "¿Qué invariante debe cumplirse siempre con lectores y escritores?",
        [
            "Que haya siempre más lectores que escritores.",
            "Que no haya lectores activos mientras un escritor usa el recurso.",
            "Que el contador compartido sea siempre positivo.",
        ],
        1,
        "Un escritor necesita acceso exclusivo, así que no puede haber lectores "
        "activos a la vez. Tampoco puede haber dos escritores simultáneos, y el "
        "número de lectores nunca puede ser negativo.",
        "readers",
    ),
    Question(
        "q10",
        "¿Qué hace una cola FIFO justa?",
        [
            "Atiende siempre primero a los lectores.",
            "Atiende las solicitudes en orden de llegada, sin adelantamientos.",
            "Ignora a los escritores.",
        ],
        1,
        "Al respetar el orden de llegada, un lector que llega después de un "
        "escritor no puede adelantarlo. Esto evita la inanición del escritor, a "
        "cambio de reducir un poco el paralelismo entre lectores.",
        "starvation",
    ),
]


class StudyView(ctk.CTkFrame):
    def __init__(self, master, app) -> None:
        super().__init__(master, fg_color=theme.BG, corner_radius=0)
        self.app = app
        self._answered: dict[str, int] = {}
        self._option_buttons: dict[str, list[ctk.CTkButton]] = {}
        self._feedback: dict[str, ctk.CTkLabel] = {}

        ctk.CTkLabel(
            self, text="Modo de estudio", font=theme.title_font(30),
            text_color=theme.CHARCOAL_DEEP,
        ).pack(anchor="w", padx=40, pady=(28, 2))
        ctk.CTkLabel(
            self, text="Elige una respuesta. Recibirás la explicación completa, no "
                      "solo si acertaste o no.",
            font=theme.ui_font(13), text_color=theme.TEXT_SEC,
        ).pack(anchor="w", padx=40, pady=(0, 10))

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=40)
        self.score_label = ctk.CTkLabel(
            bar, text="Aciertos: 0 / 0", font=theme.ui_font(13, "bold"),
            text_color=theme.BLUE_DARK,
        )
        self.score_label.pack(side="left")
        ctk.CTkButton(
            bar, text="Reiniciar respuestas", height=34, corner_radius=9,
            fg_color=theme.BEIGE, hover_color=theme.STONE, text_color=theme.CHARCOAL,
            font=theme.ui_font(12, "bold"), command=self._restart,
        ).pack(side="right")

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=32, pady=14)

        for q in QUESTIONS:
            card = ctk.CTkFrame(scroll, fg_color=theme.PAPER, corner_radius=14,
                                border_width=1, border_color=theme.BEIGE)
            card.pack(fill="x", pady=7, padx=6)
            ctk.CTkLabel(
                card, text=q.text, font=theme.ui_font(14, "bold"),
                text_color=theme.CHARCOAL, wraplength=980, justify="left",
            ).pack(anchor="w", padx=18, pady=(14, 8))

            self._option_buttons[q.key] = []
            for idx, option in enumerate(q.options):
                btn = ctk.CTkButton(
                    card, text=f"{chr(65 + idx)}.  {option}", anchor="w", height=38,
                    corner_radius=9, fg_color=theme.BG, hover_color=theme.BEIGE,
                    text_color=theme.TEXT, font=theme.ui_font(13),
                    command=lambda k=q.key, i=idx: self._answer(k, i),
                )
                btn.pack(fill="x", padx=18, pady=3)
                self._option_buttons[q.key].append(btn)

            feedback = ctk.CTkLabel(
                card, text="", font=theme.ui_font(12), text_color=theme.TEXT_SEC,
                wraplength=980, justify="left",
            )
            feedback.pack(anchor="w", padx=18, pady=(4, 14))
            self._feedback[q.key] = feedback

    def _answer(self, key: str, choice: int) -> None:
        if key in self._answered:
            return
        self._answered[key] = choice
        question = next(q for q in QUESTIONS if q.key == key)
        buttons = self._option_buttons[key]
        for idx, btn in enumerate(buttons):
            if idx == question.correct:
                btn.configure(fg_color=theme.SAGE, text_color=theme.PAPER)
            elif idx == choice:
                btn.configure(fg_color=theme.RED, text_color=theme.PAPER)
            btn.configure(state="disabled")
        correct = choice == question.correct
        prefix = "✓ Correcto. " if correct else "✗ No exactamente. "
        self._feedback[key].configure(
            text=prefix + question.explanation,
            text_color=theme.SAGE if correct else theme.CHARCOAL,
        )
        self._update_score()

    def _update_score(self) -> None:
        hits = 0
        for key, choice in self._answered.items():
            q = next(q for q in QUESTIONS if q.key == key)
            if choice == q.correct:
                hits += 1
        self.score_label.configure(
            text=f"Aciertos: {hits} / {len(self._answered)} "
                 f"(de {len(QUESTIONS)} preguntas)"
        )

    def _restart(self) -> None:
        self._answered.clear()
        for key, buttons in self._option_buttons.items():
            q = next(q for q in QUESTIONS if q.key == key)
            for idx, btn in enumerate(buttons):
                btn.configure(state="normal", fg_color=theme.BG, text_color=theme.TEXT)
            self._feedback[key].configure(text="")
        self._update_score()
