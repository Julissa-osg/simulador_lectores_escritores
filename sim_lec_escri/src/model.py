"""model.py — El modelo de datos de SimOS Lab.

Este archivo agrupa TODO lo que describe "qué hay" en la simulación:
los hilos y sus micro-operaciones, los eventos que produce cada paso, el
recurso compartido y el registro cronológico de eventos.

IMPORTANTE: los "hilos" son una ABSTRACCIÓN EDUCATIVA, no hilos reales del
sistema operativo. El motor avanza un evento cada vez y cambia el estado de
estos objetos para reproducir lo que ocurriría en un sistema real.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ==============================================================================
# SECCIÓN 1 · ESTADOS, HILOS Y MICRO-OPERACIONES
# ==============================================================================

class ThreadState(str, Enum):
    """Estados visibles de un hilo en el modelo educativo."""

    LISTO = "Listo"
    EJECUTANDO = "Ejecutando"
    ESPERANDO = "Esperando"
    BLOQUEADO = "Bloqueado"
    TERMINADO = "Terminado"


class ThreadKind(str, Enum):
    """Tipo de hilo según el papel que juega sobre el recurso compartido."""

    LECTOR = "lector"
    ESCRITOR = "escritor"


# Micro-operaciones. Un programa de hilo es una lista de estas operaciones.
OP_SOLICITAR = "SOLICITAR"          # pide acceso al recurso compartido
OP_LIBERAR = "LIBERAR"              # libera el acceso
OP_LEER_DATO = "LEER_DATO"          # copia el valor compartido a memoria local
OP_ESCRIBIR_DATO = "ESCRIBIR_DATO"  # escribe la memoria local en el recurso
OP_CALCULAR = "CALCULAR"            # opera sobre la memoria local (arg = delta)
OP_USAR = "USAR"                    # trabajo dentro de la sección crítica (arg = texto)
OP_ESPERAR = "ESPERAR"              # espera planificada; no toca el recurso
OP_ADQUIRIR = "ADQUIRIR"            # toma un recurso exclusivo (arg = id de recurso)
OP_SOLTAR = "SOLTAR"                # suelta un recurso exclusivo (arg = id de recurso)
OP_TERMINAR = "TERMINAR"            # fin del programa del hilo


@dataclass
class MicroOp:
    """Una sola acción de un hilo. El motor ejecuta una por paso."""

    op: str
    arg: Any = None
    note: str = ""


@dataclass
class SimThread:
    """Un hilo simulado con su programa y su estado actual.

    Attributes:
        tid: identificador corto e interno, por ejemplo ``L1`` o ``E2``.
        kind: lector o escritor.
        label: nombre legible, por ejemplo ``Lector 1``.
        program: lista de micro-operaciones que debe ejecutar.
        state: estado actual dentro del modelo educativo.
        pc: program counter, índice de la siguiente micro-operación.
        local_value: copia local del dato compartido (escenario de carrera).
        waiting_since: evento en el que empezó a esperar, para medir la espera.
        blocked_reason: texto que explica por qué está esperando o bloqueado.
        holds: conjunto de recursos exclusivos retenidos (escenario de deadlock).
    """

    tid: str
    kind: ThreadKind
    label: str
    program: list[MicroOp]
    state: ThreadState = ThreadState.LISTO
    pc: int = 0
    local_value: Optional[int] = None
    waiting_since: Optional[int] = None
    blocked_reason: str = ""
    holds: set[str] = field(default_factory=set)

    @property
    def finished(self) -> bool:
        return self.state is ThreadState.TERMINADO

    @property
    def current_op(self) -> Optional[MicroOp]:
        if self.pc < len(self.program):
            return self.program[self.pc]
        return None

    def advance(self) -> None:
        self.pc += 1

    def block(self, event_number: int, reason: str) -> None:
        self.state = ThreadState.ESPERANDO
        if self.waiting_since is None:
            self.waiting_since = event_number
        self.blocked_reason = reason

    def hard_block(self, event_number: int, reason: str) -> None:
        """Bloqueo que no se resolverá solo (por ejemplo un interbloqueo)."""
        self.state = ThreadState.BLOQUEADO
        self.waiting_since = event_number
        self.blocked_reason = reason

    def wake(self) -> None:
        self.state = ThreadState.LISTO
        self.waiting_since = None
        self.blocked_reason = ""

    def to_dict(self) -> dict:
        return {
            "tid": self.tid,
            "kind": self.kind.value,
            "label": self.label,
            "state": self.state.value,
            "pc": self.pc,
            "local_value": self.local_value,
            "blocked_reason": self.blocked_reason,
            "holds": sorted(self.holds),
        }


# ==============================================================================
# SECCIÓN 2 · EVENTOS
# ==============================================================================

class EventType(str, Enum):
    """Tipos de evento que el registro puede contener."""

    SIM_INICIO = "SIM_INICIO"
    LECTOR_SOLICITA_ACCESO = "LECTOR_SOLICITA_ACCESO"
    LECTOR_ENTRA = "LECTOR_ENTRA"
    LECTOR_LEE = "LECTOR_LEE"
    LECTOR_TERMINA = "LECTOR_TERMINA"
    ESCRITOR_SOLICITA_ACCESO = "ESCRITOR_SOLICITA_ACCESO"
    ESCRITOR_ENTRA = "ESCRITOR_ENTRA"
    ESCRITOR_LEE_DATO = "ESCRITOR_LEE_DATO"
    ESCRITOR_CALCULA = "ESCRITOR_CALCULA"
    ESCRITOR_MODIFICA_DATO = "ESCRITOR_MODIFICA_DATO"
    ESCRITOR_TERMINA = "ESCRITOR_TERMINA"
    HILO_BLOQUEADO = "HILO_BLOQUEADO"
    HILO_DESBLOQUEADO = "HILO_DESBLOQUEADO"
    HILO_TRABAJA = "HILO_TRABAJA"
    CAMBIO_DE_CONTEXTO = "CAMBIO_DE_CONTEXTO"
    SEMAFORO_WAIT = "SEMAFORO_WAIT"
    SEMAFORO_SIGNAL = "SEMAFORO_SIGNAL"
    MONITOR_WAIT = "MONITOR_WAIT"
    MONITOR_SIGNAL = "MONITOR_SIGNAL"
    RECURSO_SOLICITADO = "RECURSO_SOLICITADO"
    RECURSO_ASIGNADO = "RECURSO_ASIGNADO"
    RECURSO_LIBERADO = "RECURSO_LIBERADO"
    INTERBLOQUEO_DETECTADO = "INTERBLOQUEO_DETECTADO"
    INVARIANTE_VIOLADO = "INVARIANTE_VIOLADO"
    FIN = "FIN"


@dataclass
class Event:
    """Una transición de estado del sistema (la unidad mínima de avance).

    Attributes:
        number: número secuencial del evento (1-based).
        type: tipo de evento.
        thread: identificador del hilo implicado, si lo hay.
        prev_state / post_state: estado del hilo antes y después.
        resource: recurso implicado (el catálogo o una variable).
        explanation: frase sencilla pensada para el usuario principiante.
        reason: motivo técnico de la transición.
        consequences: cambios secundarios de este mismo paso, por ejemplo
            otros hilos que se desbloquean al liberar un recurso.
        event_time: tiempo simulado (ticks del modelo) del evento.
        context_switch_from: hilo que tenía la CPU antes de este evento.
    """

    number: int
    type: EventType
    thread: Optional[str] = None
    prev_state: Optional[str] = None
    post_state: Optional[str] = None
    resource: Optional[str] = None
    explanation: str = ""
    reason: str = ""
    consequences: list[str] = field(default_factory=list)
    event_time: int = 0
    context_switch_from: Optional[str] = None

    def to_dict(self) -> dict:
        """Versión serializable, útil para pruebas y para exportar el historial."""
        return {
            "number": self.number,
            "type": self.type.value,
            "thread": self.thread,
            "prev_state": self.prev_state,
            "post_state": self.post_state,
            "resource": self.resource,
            "explanation": self.explanation,
            "reason": self.reason,
            "consequences": list(self.consequences),
            "event_time": self.event_time,
            "context_switch_from": self.context_switch_from,
        }

    def short(self) -> str:
        """Línea compacta para el registro de la interfaz."""
        who = self.thread if self.thread else "Sistema"
        return f"Evento {self.number:02d} — {who}: {self.explanation}"


# ==============================================================================
# SECCIÓN 3 · RECURSO COMPARTIDO
# ==============================================================================

@dataclass
class ChangeRecord:
    """Un cambio de valor registrado en el recurso compartido."""

    event_number: int
    old_value: int
    new_value: int
    by: str


@dataclass
class SharedResource:
    """El catálogo compartido de la biblioteca.

    Guarda el dato compartido y la trazabilidad de sus cambios. Los contadores
    de lectores/escritores activos viven en el mecanismo de sincronización.
    """

    name: str = "Catálogo"
    value: int = 100
    initial_value: int = 100
    history: list[ChangeRecord] = field(default_factory=list)
    expected_value: int = 100

    def reset(self) -> None:
        self.value = self.initial_value
        self.expected_value = self.initial_value
        self.history.clear()

    def read(self) -> int:
        """Devuelve el valor actual. No modifica nada."""
        return self.value

    def write(self, new_value: int, by: str, event_number: int) -> ChangeRecord:
        """Escribe un nuevo valor y deja traza del cambio."""
        old = self.value
        self.value = new_value
        record = ChangeRecord(event_number, old, new_value, by)
        self.history.append(record)
        return record

    @property
    def updates_lost(self) -> int:
        """Actualizaciones correctas perdidas respecto a lo esperado."""
        return max(0, self.expected_value - self.value)

    @property
    def is_consistent(self) -> bool:
        """El recurso es consistente si su valor coincide con lo esperado."""
        return self.value == self.expected_value

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "initial_value": self.initial_value,
            "expected_value": self.expected_value,
            "is_consistent": self.is_consistent,
            "updates_lost": self.updates_lost,
            "history": [
                {"event": h.event_number, "from": h.old_value, "to": h.new_value, "by": h.by}
                for h in self.history
            ],
        }


@dataclass
class ExclusiveResource:
    """Recurso binario para el escenario de interbloqueo.

    Tiene un único propietario a la vez y una cola de hilos esperando.
    """

    rid: str
    name: str
    owner: str | None = None
    waiting: list[str] = field(default_factory=list)

    @property
    def free(self) -> bool:
        return self.owner is None

    def to_dict(self) -> dict:
        return {
            "rid": self.rid,
            "name": self.name,
            "owner": self.owner,
            "waiting": list(self.waiting),
        }


# ==============================================================================
# SECCIÓN 4 · REGISTRO DE EVENTOS
# ==============================================================================

class EventLog:
    """Guarda los eventos en orden y permite filtrarlos.

    Es la fuente de verdad del panel de historial de la interfaz. Nunca se
    reescribe un evento: cada paso añade uno nuevo.
    """

    def __init__(self) -> None:
        self._events: list[Event] = []

    def add(self, event: Event) -> None:
        self._events.append(event)

    def clear(self) -> None:
        self._events.clear()

    def __len__(self) -> int:
        return len(self._events)

    def __iter__(self):
        return iter(self._events)

    @property
    def events(self) -> list[Event]:
        return list(self._events)

    @property
    def last(self) -> Optional[Event]:
        return self._events[-1] if self._events else None

    def filter(
        self,
        thread: Optional[str] = None,
        event_type: Optional[EventType] = None,
        scenario: Optional[str] = None,  # reservado para uso futuro
    ) -> list[Event]:
        """Devuelve los eventos que cumplen los filtros indicados."""
        result: list[Event] = []
        for event in self._events:
            if thread is not None and event.thread != thread:
                continue
            if event_type is not None and event.type is not event_type:
                continue
            result.append(event)
        return result

    def threads_seen(self) -> list[str]:
        seen: list[str] = []
        for event in self._events:
            if event.thread and event.thread not in seen:
                seen.append(event.thread)
        return seen

    def as_text(self) -> str:
        return "\n".join(event.short() for event in self._events)

    def to_list(self) -> list[dict]:
        return [event.to_dict() for event in self._events]