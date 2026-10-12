"""sync.py — Toda la sincronización de SimOS Lab.

Este archivo agrupa:

1. Las **reglas de admisión** de lectores/escritores y las políticas de equidad
   (la clase base ``ReadersWritersSync``, sus implementaciones y el modo nulo).
2. La primitiva de **semáforo** y el mecanismo lectores/escritores con semáforos.
3. Las **variables de condición**, el **monitor** y el mecanismo con monitor.
4. La fábrica ``create_sync()`` que el motor usa para construir el mecanismo.

Diseño: los mecanismos de semáforo y monitor reutilizan las REGLAS de
``ReadersWritersSync`` y solo cambian la FORMA de representar el estado.
"""

from __future__ import annotations

from abc import ABC
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from .model import SimThread, ThreadKind

# ---------------------------------------------------------------------------
# Constantes de políticas y mecanismos
# ---------------------------------------------------------------------------
POLICY_READERS_FIRST = "readers_first"
POLICY_FAIR = "fair"

MECH_NONE = "none"
MECH_SEMAPHORE = "semaphore"
MECH_MONITOR = "monitor"


# ==============================================================================
# SECCIÓN 1 · REGLAS DE ADMISIÓN Y POLÍTICAS
# ==============================================================================

@dataclass
class GrantResult:
    """Resultado de una solicitud de acceso."""

    granted: bool
    reason: str = ""
    also_granted: list[str] = field(default_factory=list)


class ReadersWritersSync(ABC):
    """Reglas de admisión compartidas por todos los mecanismos.

    Mantiene quién está leyendo, quién escribe y quién espera. Las subclases
    añaden la representación propia (semáforos o monitores).

    Dos políticas:
    * ``readers_first``: mientras no haya un escritor *activo*, los lectores
      pueden entrar aunque haya escritores esperando. Es la clásica y **puede
      producir inanición de escritores**.
    * ``fair``: cola FIFO estricta. Un lector que llega después de un escritor
      esperando no puede adelantarlo.
    """

    mechanism = MECH_NONE

    def __init__(self, policy: str = POLICY_READERS_FIRST) -> None:
        self.policy = policy
        self.active_readers: set[str] = set()
        self.active_writers: set[str] = set()
        self.waiting: deque[tuple[str, ThreadKind]] = deque()
        self.initial_value = None  # para semáforo/monitor

    # --------------------------- propiedades ---------------------------
    @property
    def active_writer(self) -> Optional[str]:
        if len(self.active_writers) == 1:
            return next(iter(self.active_writers))
        return None

    @property
    def reader_count(self) -> int:
        return len(self.active_readers)

    @property
    def writer_count(self) -> int:
        return len(self.active_writers)

    def is_active(self, tid: str) -> bool:
        return tid in self.active_readers or tid in self.active_writers

    # --------------------------- operaciones ---------------------------
    def request(self, thread: SimThread) -> GrantResult:
        """El hilo pide acceso. Devuelve si entra ahora o queda esperando."""
        self.waiting.append((thread.tid, thread.kind))
        before = self._active_ids()
        self._dispatch()
        after = self._active_ids()
        newly = [t for t in after if t not in before]
        granted = thread.tid in after
        if granted:
            reason = self._grant_reason(thread)
        else:
            reason = self._block_reason(thread)
        others = [t for t in newly if t != thread.tid]
        return GrantResult(granted=granted, reason=reason, also_granted=others)

    def release(self, thread: SimThread) -> list[str]:
        """El hilo termina su acceso. Devuelve los hilos recién desbloqueados."""
        if thread.tid in self.active_readers:
            self.active_readers.discard(thread.tid)
        elif thread.tid in self.active_writers:
            self.active_writers.discard(thread.tid)
        before = self._active_ids()
        self._dispatch()
        after = self._active_ids()
        return [t for t in after if t not in before]

    # --------------------------- despacho ---------------------------
    def _dispatch(self) -> None:
        """Admite tantos hilos en espera como permita la política."""
        if self.policy == POLICY_FAIR:
            self._dispatch_fair()
        else:
            self._dispatch_readers_first()

    def _dispatch_readers_first(self) -> None:
        """Política clásica: los lectores no esperan a escritores pendientes."""
        i = 0
        while i < len(self.waiting):
            tid, kind = self.waiting[i]
            if kind is ThreadKind.LECTOR and not self.active_writers:
                self.waiting.remove(self.waiting[i])
                self.active_readers.add(tid)
                continue
            if (
                kind is ThreadKind.ESCRITOR
                and not self.active_writers
                and not self.active_readers
            ):
                self.waiting.remove(self.waiting[i])
                self.active_writers.add(tid)
                continue
            i += 1

    def _dispatch_fair(self) -> None:
        """Cola FIFO estricta: solo se atiende al primero de la cola."""
        while self.waiting:
            tid, kind = self.waiting[0]
            if kind is ThreadKind.LECTOR:
                if self.active_writers:
                    break
                self.waiting.popleft()
                self.active_readers.add(tid)
            else:
                if self.active_writers or self.active_readers:
                    break
                self.waiting.popleft()
                self.active_writers.add(tid)

    # --------------------------- textos ---------------------------
    def _grant_reason(self, thread: SimThread) -> str:
        if thread.kind is ThreadKind.LECTOR:
            if not self.active_writers:
                return "Hay acceso de lectura disponible; puede compartir el recurso."
            return "Se le concede el acceso."
        return "Nadie más usa el recurso; obtiene acceso exclusivo."

    def _block_reason(self, thread: SimThread) -> str:
        if thread.kind is ThreadKind.LECTOR:
            return "Un escritor está modificando el recurso; los lectores esperan."
        if self.policy == POLICY_FAIR and self.active_readers:
            return "Hay lectores activos y la cola justa no le permite adelantarlos."
        if self.active_readers:
            return "Hay lectores activos; el escritor necesita acceso exclusivo."
        if self.active_writers:
            return "Otro escritor usa el recurso en exclusiva."
        return "El recurso no está disponible todavía."

    # --------------------------- invariantes ---------------------------
    def check_invariants(self) -> list[str]:
        """Devuelve una lista de invariantes violados (vacía si todo está bien)."""
        problems: list[str] = []
        if not self.is_enforcing:
            return problems
        if self.active_readers and self.active_writers:
            problems.append(
                "Hay lectores y escritores activos al mismo tiempo."
            )
        if len(self.active_writers) > 1:
            problems.append("Hay más de un escritor activo simultáneamente.")
        return problems

    @property
    def is_enforcing(self) -> bool:
        """True si el mecanismo realmente aplica exclusión (no es NullSync)."""
        return True

    def can_read(self, tid: str) -> bool:
        return tid in self.active_readers

    def can_write(self, tid: str) -> bool:
        return tid in self.active_writers

    # --------------------------- helpers ---------------------------
    def _active_ids(self) -> set[str]:
        return set(self.active_readers) | set(self.active_writers)

    def snapshot(self) -> dict:
        return {
            "mechanism": self.mechanism,
            "policy": self.policy,
            "active_readers": sorted(self.active_readers),
            "active_writers": sorted(self.active_writers),
            "waiting": [{"tid": t, "kind": k.value} for t, k in self.waiting],
            "readers_count": len(self.active_readers),
            "writers_count": len(self.active_writers),
        }


class NullSync(ReadersWritersSync):
    """Sin sincronización: todos entran siempre.

    Sirve para demostrar condiciones de carrera. Los invariantes de exclusión
    mutua NO se aplican en este modo porque queremos que se puedan romper.
    """

    mechanism = MECH_NONE

    def request(self, thread: SimThread) -> GrantResult:
        if thread.kind is ThreadKind.LECTOR:
            self.active_readers.add(thread.tid)
            return GrantResult(True, "Entra sin ninguna protección (riesgo de carrera).")
        self.active_writers.add(thread.tid)
        return GrantResult(True, "Escribe sin ninguna protección (riesgo de carrera).")

    def release(self, thread: SimThread) -> list[str]:
        self.active_readers.discard(thread.tid)
        self.active_writers.discard(thread.tid)
        return []

    def check_invariants(self) -> list[str]:
        return []

    @property
    def is_enforcing(self) -> bool:
        return False


# ==============================================================================
# SECCIÓN 2 · SEMÁFOROS
# ==============================================================================

@dataclass
class Semaphore:
    """Semáforo contador con cola de hilos bloqueados.

    Un semáforo es un contador entero protegido con dos operaciones atómicas:
    ``wait`` (P) espera a que el contador sea mayor que cero y lo decrementa
    (si es cero, el hilo queda bloqueado) y ``signal`` (V) lo incrementa o
    despierta a un bloqueado (handoff). Es un modelo educativo: no usa la
    primitiva real de ninguna librería, solo muestra su comportamiento.

    Attributes:
        name: nombre visible del semáforo.
        value: valor actual (nunca negativo mientras no haya bloqueados).
        blocked: hilos esperando permiso, en orden de llegada.
        history: registro de operaciones para explicar su evolución.
    """

    name: str
    value: int = 1
    blocked: deque[str] = field(default_factory=deque)
    history: list[str] = field(default_factory=list)

    def wait(self, tid: str) -> bool:
        """Intenta tomar el semáforo. Devuelve True si lo obtuvo."""
        if self.value > 0:
            self.value -= 1
            self.history.append(f"{tid} hace wait -> valor {self.value}")
            return True
        if tid not in self.blocked:
            self.blocked.append(tid)
        self.history.append(f"{tid} hace wait y queda bloqueado (valor 0)")
        return False

    def signal(self) -> Optional[str]:
        """Libera el semáforo. Devuelve el hilo desbloqueado, si lo hay."""
        if self.blocked:
            tid = self.blocked.popleft()
            # Handoff: el permiso pasa directamente al hilo desbloqueado.
            self.history.append(f"signal -> desbloquea a {tid} (handoff)")
            return tid
        self.value += 1
        self.history.append(f"signal -> valor {self.value}")
        return None

    def reset(self, value: int = 1) -> None:
        self.value = value
        self.blocked.clear()
        self.history.clear()

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "blocked": list(self.blocked),
        }


class SemaphoreMechanism(ReadersWritersSync):
    """Lectores/escritores resuelto con semáforos.

    Representación clásica:
    * ``wrt`` protege el acceso exclusivo del escritor (y del primer/último lector).
    * ``mutex`` protege el contador ``read_count``.
    * ``read_count`` cuenta lectores activos.

    En este modelo la actualización de ``read_count`` se realiza de forma
    atómica (no se observa bloqueo en ``mutex``); es una simplificación
    documentada que no altera el comportamiento educativo.
    """

    mechanism = MECH_SEMAPHORE

    def __init__(self, policy: str = POLICY_READERS_FIRST) -> None:
        super().__init__(policy=policy)
        self.wrt = Semaphore("wrt", 1)
        self.mutex = Semaphore("mutex", 1)
        self.read_count = 0
        self._sync_wrt_from_state()

    def _sync_wrt_from_state(self) -> None:
        """Mantiene la representación del semáforo ``wrt`` coherente con el estado."""
        self.wrt.value = 0 if self.active_writers else 1
        self.wrt.blocked = deque(t for t, k in self.waiting if k.value == "escritor")

    def request(self, thread) -> GrantResult:
        result = super().request(thread)
        if result.granted:
            if thread.kind.value == "lector":
                self.read_count += 1
                self.wrt.history.append(
                    f"{thread.tid} entra como lector (read_count={self.read_count})"
                )
            else:
                self.wrt.history.append(f"{thread.tid} toma wrt -> 0")
        self._sync_wrt_from_state()
        return result

    def release(self, thread) -> list[str]:
        if thread.tid in self.active_readers:
            self.read_count = max(0, self.read_count - 1)
            self.wrt.history.append(
                f"{thread.tid} sale como lector (read_count={self.read_count})"
            )
        elif thread.tid in self.active_writers:
            self.wrt.history.append(f"{thread.tid} libera wrt -> 1")
        newly = super().release(thread)
        self._sync_wrt_from_state()
        return newly

    def snapshot(self) -> dict:
        data = super().snapshot()
        data["semaphores"] = [self.wrt.to_dict(), self.mutex.to_dict()]
        data["read_count"] = self.read_count
        return data


# ==============================================================================
# SECCIÓN 3 · MONITORES Y VARIABLES DE CONDICIÓN
# ==============================================================================

@dataclass
class Condition:
    """Variable de condición con su cola de hilos suspendidos.

    Permite a un hilo esperar hasta que se cumpla una condición. Regla de oro:
    al reanudar hay que **volver a comprobar la condición** (bucle ``while``),
    porque entre el ``signal`` y la reanudación el estado pudo cambiar.
    """

    name: str
    waiters: deque[str] = field(default_factory=deque)
    history: list[str] = field(default_factory=list)

    def wait(self, tid: str) -> None:
        if tid not in self.waiters:
            self.waiters.append(tid)
        self.history.append(f"{tid} hace wait en '{self.name}'")

    def signal(self) -> str | None:
        if self.waiters:
            tid = self.waiters.popleft()
            self.history.append(f"signal en '{self.name}' -> despierta {tid}")
            return tid
        self.history.append(f"signal en '{self.name}' sin nadie esperando")
        return None

    def notify_all(self) -> list[str]:
        woken = list(self.waiters)
        self.waiters.clear()
        self.history.append(f"notify_all en '{self.name}' -> {len(woken)} hilos")
        return woken

    def to_dict(self) -> dict:
        return {"name": self.name, "waiters": list(self.waiters)}


class Monitor:
    """Monitor con un estado protegido y varias variables de condición.

    Un monitor agrupa el estado compartido y las operaciones que lo modifican.
    Solo un hilo puede estar "dentro" a la vez: el propio monitor garantiza la
    exclusión mutua (``lock_owner``), el programador no manipula candados.

    Se usa la política de señalización **signal-and-continue**: el hilo que hace
    ``signal`` conserva el monitor y el despertado se re-evalúa después.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.lock_owner: str | None = None
        self.conditions: dict[str, Condition] = {}

    def condition(self, name: str) -> Condition:
        if name not in self.conditions:
            self.conditions[name] = Condition(name)
        return self.conditions[name]

    def enter(self, tid: str) -> None:
        self.lock_owner = tid

    def exit(self, tid: str) -> None:
        if self.lock_owner == tid:
            self.lock_owner = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "lock_owner": self.lock_owner,
            "conditions": [c.to_dict() for c in self.conditions.values()],
        }


class MonitorMechanism(ReadersWritersSync):
    """Lectores/escritores resuelto con un monitor.

    Condiciones usadas:
    * ``pueden_leer``: los lectores esperan aquí si hay un escritor activo.
    * ``puede_escribir``: los escritores esperan aquí si hay lectores o un
      escritor activos.

    El monitor garantiza la exclusión mutua; el acceso efectivo lo decide la
    condición comprobada en bucle, no un candado manual.
    """

    mechanism = MECH_MONITOR

    def __init__(self, policy: str = POLICY_READERS_FIRST) -> None:
        super().__init__(policy=policy)
        self.monitor = Monitor("CatalogoMonitor")
        self.can_read = self.monitor.condition("pueden_leer")
        self.can_write = self.monitor.condition("puede_escribir")

    def _refresh_conditions(self) -> None:
        self.can_read.waiters = deque(t for t, k in self.waiting if k.value == "lector")
        self.can_write.waiters = deque(t for t, k in self.waiting if k.value == "escritor")

    def request(self, thread) -> GrantResult:
        self.monitor.enter(thread.tid)
        result = super().request(thread)
        if result.granted:
            self.monitor.exit(thread.tid)
        else:
            # Al no cumplirse la condición, el hilo queda suspendido en su variable.
            cond = self.can_read if thread.kind.value == "lector" else self.can_write
            cond.history.append(f"{thread.tid} re-evalúa condición y espera")
            self.monitor.exit(thread.tid)
        self._refresh_conditions()
        return result

    def release(self, thread) -> list[str]:
        newly = super().release(thread)
        for tid in newly:
            self.can_write.signal()
            self.can_read.signal()
        self._refresh_conditions()
        return newly

    def snapshot(self) -> dict:
        data = super().snapshot()
        data["monitor"] = self.monitor.to_dict()
        return data


# ==============================================================================
# SECCIÓN 4 · FÁBRICA DE MECANISMOS
# ==============================================================================

def create_sync(mechanism: str, policy: str = POLICY_READERS_FIRST) -> ReadersWritersSync:
    """Construye el mecanismo de sincronización que pide un escenario."""
    if mechanism == MECH_NONE:
        return NullSync(policy=POLICY_READERS_FIRST)
    if mechanism == MECH_SEMAPHORE:
        return SemaphoreMechanism(policy=policy)
    if mechanism == MECH_MONITOR:
        return MonitorMechanism(policy=policy)
    raise ValueError(f"Mecanismo desconocido: {mechanism}")