"""engine.py — El motor de simulación determinista.

El motor es **independiente de la interfaz**. La interfaz solo consulta
``snapshot()`` y ordena ``step()``. Cada llamada a :meth:`SimulationEngine.step`
ejecuta EXACTAMENTE una micro-operación de exactamente un hilo y devuelve el
evento producido.

El planificador es round-robin FIFO determinista sobre los hilos "Listos". Esto
hace que las intercalaciones sean reproducibles (no dependen de la velocidad de
la máquina), lo cual es imprescindible para demostrar la condición de carrera de
forma controlada.
"""

from __future__ import annotations

import copy
from collections import deque
from typing import Optional

from .model import (
    Event,
    EventLog,
    EventType,
    ExclusiveResource,
    SharedResource,
    OP_ADQUIRIR,
    OP_CALCULAR,
    OP_ESCRIBIR_DATO,
    OP_ESPERAR,
    OP_LEER_DATO,
    OP_LIBERAR,
    OP_SOLICITAR,
    OP_SOLTAR,
    OP_TERMINAR,
    OP_USAR,
    MicroOp,
    SimThread,
    ThreadKind,
    ThreadState,
)
from .sync import create_sync


class SimulationEngine:
    """Interpreta los programas de los hilos y coordina el acceso al recurso."""

    def __init__(self, config) -> None:
        self.config = config
        self.reset()

    # =====================================================================
    # Ciclo de vida
    # =====================================================================
    def reset(self) -> None:
        """Devuelve el motor al estado inicial definido por el escenario."""
        cfg = self.config
        self.event_counter = 0
        self.time = 0
        self.log = EventLog()
        self.resource = SharedResource(
            name="Catálogo",
            value=cfg.initial_value,
            initial_value=cfg.initial_value,
            expected_value=cfg.expected_value,
        )
        self.sync = create_sync(cfg.sync_mechanism, cfg.sync_policy)
        self.threads: dict[str, SimThread] = {
            t.tid: t for t in cfg.threads_factory()
        }
        self.exclusive: dict[str, ExclusiveResource] = {
            r.rid: r for r in cfg.resources_factory()
        }
        self.ready_queue: deque[str] = deque(t.tid for t in self.threads.values())
        self.current: Optional[str] = None
        self.context_switches = 0
        self.timeline: list[tuple[int, str]] = []
        self.finished = False
        self.deadlock_detected = False
        self.warnings: list[str] = []
        self.max_wait: dict[str, int] = {tid: 0 for tid in self.threads}
        self._initial_emit()

    def _initial_emit(self) -> None:
        self.event_counter += 1
        event = self._emit(
            EventType.SIM_INICIO,
            explanation=f"Comienza el escenario «{self.config.title}».",
            reason=(
                f"Mecanismo: {self.config.sync_mechanism} · "
                f"Política: {self.config.sync_policy}"
            ),
            number=self.event_counter,
        )
        self.log.add(event)

    # =====================================================================
    # Avance
    # =====================================================================
    def step(self) -> Optional[Event]:
        """Ejecuta una micro-operación y devuelve el evento. ``None`` si acabó."""
        if self.finished:
            return None

        prev_current = self.current
        if self.ready_queue:
            tid = self.ready_queue.popleft()
            # Reencolar al anterior si sigue pudiendo ejecutar (round-robin).
            if prev_current is not None and prev_current != tid:
                prev = self.threads[prev_current]
                if prev.state is ThreadState.EJECUTANDO and not prev.finished:
                    prev.state = ThreadState.LISTO
                    self.ready_queue.append(prev_current)
        else:
            # No hay cola: solo el hilo actual puede continuar si sigue en la CPU.
            current = self.threads.get(prev_current) if prev_current else None
            if current is None or current.state is not ThreadState.EJECUTANDO or current.finished:
                return self._finish_simulation()
            tid = prev_current

        thread = self.threads[tid]
        self.current = tid
        thread.state = ThreadState.EJECUTANDO
        self.timeline.append((self.event_counter + 1, tid))

        self.event_counter += 1
        number = self.event_counter
        event = self._execute(thread, number)

        # Metadatos de cambio de contexto (solo informativo).
        if prev_current is not None and prev_current != tid:
            event.context_switch_from = prev_current
            self.context_switches += 1

        # Actualiza tiempos de espera de los hilos que siguen esperando.
        for other in self.threads.values():
            if other.state in (ThreadState.ESPERANDO, ThreadState.BLOQUEADO):
                if other.waiting_since is not None:
                    waited = number - other.waiting_since
                    self.max_wait[other.tid] = max(self.max_wait[other.tid], waited)

        self._enforce_invariants(event)
        self.log.add(event)
        return event

    def run_until_end(self, max_steps: int = 2000) -> list[Event]:
        """Avanza hasta terminar (útil para pruebas). Devuelve los eventos."""
        produced: list[Event] = []
        while not self.finished and max_steps > 0:
            event = self.step()
            if event is None:
                break
            produced.append(event)
            max_steps -= 1
        return produced

    def _finish_simulation(self) -> Optional[Event]:
        self.finished = True
        blocked = [
            t for t in self.threads.values()
            if t.state in (ThreadState.ESPERANDO, ThreadState.BLOQUEADO)
        ]
        if blocked:
            names = ", ".join(t.label for t in blocked)
            reason = f"Hilos que no pueden continuar: {names}."
        else:
            reason = "Todos los hilos han terminado."
        self.event_counter += 1
        event = Event(
            number=self.event_counter,
            type=EventType.FIN,
            explanation="La simulación ha finalizado.",
            reason=reason,
            event_time=self.time,
        )
        self.log.add(event)
        return event

    # =====================================================================
    # Ejecución de micro-operaciones
    # =====================================================================
    def _execute(self, thread: SimThread, number: int) -> Event:
        op = thread.current_op
        if op is None:
            return self._op_terminar(thread, MicroOp(OP_TERMINAR), number)
        handler = self._HANDLERS.get(op.op)
        if handler is None:
            return self._unknown_op(thread, op, number)
        return handler(self, thread, op, number)

    def _op_solicitar(self, thread: SimThread, op: MicroOp, number: int) -> Event:
        result = self.sync.request(thread)
        consequences: list[str] = []
        for other_tid in result.also_granted:
            consequences.extend(self._wake_thread(other_tid))

        prev = thread.state.value
        if result.granted:
            thread.advance()
            thread.state = ThreadState.EJECUTANDO
            if thread.kind is ThreadKind.LECTOR:
                etype = EventType.LECTOR_ENTRA
                explanation = f"{thread.label} solicita leer y entra al recurso compartido."
            else:
                etype = EventType.ESCRITOR_ENTRA
                explanation = (
                    f"{thread.label} solicita escribir y entra en la sección crítica."
                )
            return self._emit(
                etype,
                thread=thread,
                prev_state=prev,
                post_state=thread.state.value,
                resource=self.resource.name,
                explanation=explanation,
                reason=result.reason,
                consequences=consequences,
                number=number,
            )

        thread.block(number, result.reason)
        return self._emit(
            EventType.HILO_BLOQUEADO,
            thread=thread,
            prev_state=prev,
            post_state=thread.state.value,
            resource=self.resource.name,
            explanation=(
                f"{thread.label} solicita acceso pero no puede entrar todavía."
            ),
            reason=result.reason,
            consequences=consequences,
            number=number,
        )

    def _op_liberar(self, thread: SimThread, op: MicroOp, number: int) -> Event:
        newly = self.sync.release(thread)
        consequences: list[str] = []
        for other_tid in newly:
            consequences.extend(self._wake_thread(other_tid))
        thread.advance()
        thread.state = ThreadState.EJECUTANDO
        return self._emit(
            EventType.HILO_DESBLOQUEADO,
            thread=thread,
            prev_state=ThreadState.EJECUTANDO.value,
            post_state=thread.state.value,
            resource=self.resource.name,
            explanation=f"{thread.label} libera su acceso al catálogo.",
            reason="Libera el permiso de acceso que tenía.",
            consequences=consequences,
            number=number,
        )

    def _op_leer_dato(self, thread: SimThread, op: MicroOp, number: int) -> Event:
        value = self.resource.read()
        thread.local_value = value
        thread.advance()
        thread.state = ThreadState.EJECUTANDO
        if thread.kind is ThreadKind.LECTOR:
            etype = EventType.LECTOR_LEE
            explanation = f"{thread.label} lee el valor actual del catálogo: {value}."
            reason = "Lectura compartida; no modifica el dato."
        else:
            etype = EventType.ESCRITOR_LEE_DATO
            explanation = (
                f"{thread.label} copia el valor actual a su memoria local: {value}."
            )
            reason = "Primer paso de una actualización de lectura-modificación-escritura."
        return self._emit(
            etype,
            thread=thread,
            prev_state=ThreadState.EJECUTANDO.value,
            post_state=thread.state.value,
            resource=self.resource.name,
            explanation=explanation,
            reason=reason,
            number=number,
        )

    def _op_calcular(self, thread: SimThread, op: MicroOp, number: int) -> Event:
        delta = op.arg if op.arg is not None else 1
        base = thread.local_value if thread.local_value is not None else 0
        thread.local_value = base + delta
        thread.advance()
        thread.state = ThreadState.EJECUTANDO
        return self._emit(
            EventType.ESCRITOR_CALCULA,
            thread=thread,
            prev_state=ThreadState.EJECUTANDO.value,
            post_state=thread.state.value,
            resource=self.resource.name,
            explanation=(
                f"{thread.label} calcula {base} + {delta} = {thread.local_value} "
                f"(todavía sin escribir)."
            ),
            reason="Opera sobre su copia local; el catálogo aún no cambia.",
            number=number,
        )

    def _op_escribir_dato(self, thread: SimThread, op: MicroOp, number: int) -> Event:
        new_value = thread.local_value if thread.local_value is not None else self.resource.value
        record = self.resource.write(new_value, thread.label, number)
        thread.advance()
        thread.state = ThreadState.EJECUTANDO
        consequences: list[str] = []
        if not self.resource.is_consistent:
            consequences.append(
                "El valor del catálogo no coincide con el esperado: "
                "se perdió una actualización."
            )
        return self._emit(
            EventType.ESCRITOR_MODIFICA_DATO,
            thread=thread,
            prev_state=ThreadState.EJECUTANDO.value,
            post_state=thread.state.value,
            resource=self.resource.name,
            explanation=(
                f"{thread.label} escribe {record.new_value} en el catálogo "
                f"(antes {record.old_value})."
            ),
            reason="Vuelca su copia local en el recurso compartido.",
            consequences=consequences,
            number=number,
        )

    def _op_usar(self, thread: SimThread, op: MicroOp, number: int) -> Event:
        """Trabajo dentro de la sección crítica (no altera el dato directamente)."""
        thread.advance()
        thread.state = ThreadState.EJECUTANDO
        if thread.kind is ThreadKind.LECTOR:
            return self._emit(
                EventType.LECTOR_LEE,
                thread=thread,
                prev_state=ThreadState.EJECUTANDO.value,
                post_state=thread.state.value,
                resource=self.resource.name,
                explanation=f"{thread.label} {op.note or 'consulta el catálogo'}.",
                reason="Lectura dentro del acceso concedido.",
                number=number,
            )
        record = self.resource.write(self.resource.value + 1, thread.label, number)
        return self._emit(
            EventType.ESCRITOR_MODIFICA_DATO,
            thread=thread,
            prev_state=ThreadState.EJECUTANDO.value,
            post_state=thread.state.value,
            resource=self.resource.name,
            explanation=(
                f"{thread.label} {op.note or 'modifica el catálogo'}: "
                f"{record.old_value} → {record.new_value}."
            ),
            reason="Modificación hecha con acceso exclusivo.",
            number=number,
        )

    def _op_esperar(self, thread: SimThread, op: MicroOp, number: int) -> Event:
        thread.advance()
        thread.state = ThreadState.EJECUTANDO
        return self._emit(
            EventType.HILO_TRABAJA,
            thread=thread,
            prev_state=ThreadState.EJECUTANDO.value,
            post_state=thread.state.value,
            explanation=f"{thread.label} trabaja fuera del recurso (aún no lo solicita).",
            reason=op.note or "Trabajo local previo a la solicitud de acceso.",
            number=number,
        )

    def _op_adquirir(self, thread: SimThread, op: MicroOp, number: int) -> Event:
        rid = op.arg
        res = self.exclusive[rid]
        if res.free:
            res.owner = thread.tid
            thread.holds.add(rid)
            thread.advance()
            thread.state = ThreadState.EJECUTANDO
            return self._emit(
                EventType.RECURSO_ASIGNADO,
                thread=thread,
                prev_state=ThreadState.EJECUTANDO.value,
                post_state=thread.state.value,
                resource=res.name,
                explanation=f"{thread.label} obtiene el recurso {res.name}.",
                reason="El recurso estaba libre; se lo asigna.",
                number=number,
            )
        # Recurso ocupado: el hilo espera.
        if thread.tid not in res.waiting:
            res.waiting.append(thread.tid)
        thread.block(number, f"necesita {res.name}, ocupado por {res.owner}")
        cycle = self._detect_cycle()
        if cycle:
            self.deadlock_detected = True
            for tid in cycle:
                t = self.threads[tid]
                t.state = ThreadState.BLOQUEADO
                t.blocked_reason = "Bloqueado por una espera circular (interbloqueo)."
            return self._emit(
                EventType.INTERBLOQUEO_DETECTADO,
                thread=thread,
                prev_state=ThreadState.EJECUTANDO.value,
                post_state=thread.state.value,
                resource=res.name,
                explanation="¡Interbloqueo! Los hilos se esperan en círculo.",
                reason="Espera circular detectada: " + " → ".join(cycle + [cycle[0]]),
                number=number,
            )
        return self._emit(
            EventType.RECURSO_SOLICITADO,
            thread=thread,
            prev_state=ThreadState.EJECUTANDO.value,
            post_state=thread.state.value,
            resource=res.name,
            explanation=(
                f"{thread.label} pide {res.name}, pero está ocupado por {res.owner}."
            ),
            reason="El hilo queda bloqueado hasta que el recurso se libere.",
            number=number,
        )

    def _op_soltar(self, thread: SimThread, op: MicroOp, number: int) -> Event:
        rid = op.arg
        res = self.exclusive[rid]
        res.owner = None
        thread.holds.discard(rid)
        thread.advance()
        thread.state = ThreadState.EJECUTANDO
        consequences: list[str] = []
        if res.waiting:
            nxt = res.waiting.pop(0)
            res.owner = nxt
            other = self.threads[nxt]
            other.holds.add(rid)
            # La adquisición ya se ha completado en el traspaso: avanzamos su pc
            # para que no vuelva a ejecutar la petición del mismo recurso.
            cur = other.current_op
            if cur is not None and cur.op == OP_ADQUIRIR and cur.arg == rid:
                other.advance()
            if other.state in (ThreadState.ESPERANDO, ThreadState.BLOQUEADO):
                other.wake()
                if nxt not in self.ready_queue:
                    self.ready_queue.append(nxt)
            consequences.append(f"{other.label} obtiene {res.name} y pasa a Listo.")
        return self._emit(
            EventType.RECURSO_LIBERADO,
            thread=thread,
            prev_state=ThreadState.EJECUTANDO.value,
            post_state=thread.state.value,
            resource=res.name,
            explanation=f"{thread.label} libera {res.name}.",
            reason="El recurso vuelve a estar disponible.",
            consequences=consequences,
            number=number,
        )

    def _op_terminar(self, thread: SimThread, op: MicroOp, number: int) -> Event:
        consequences: list[str] = []
        # Libera el acceso al recurso compartido si lo tenía.
        if self.sync.is_active(thread.tid):
            newly = self.sync.release(thread)
            for other_tid in newly:
                consequences.extend(self._wake_thread(other_tid))
        # Libera recursos exclusivos retenidos (seguridad ante errores).
        for rid in list(thread.holds):
            res = self.exclusive[rid]
            res.owner = None
            thread.holds.discard(rid)
        thread.state = ThreadState.TERMINADO
        if thread.kind is ThreadKind.LECTOR:
            etype = EventType.LECTOR_TERMINA
            explanation = f"{thread.label} termina su lectura y libera el acceso."
        else:
            etype = EventType.ESCRITOR_TERMINA
            explanation = f"{thread.label} termina de escribir y libera el acceso."
        return self._emit(
            etype,
            thread=thread,
            prev_state=ThreadState.EJECUTANDO.value,
            post_state=thread.state.value,
            resource=self.resource.name,
            explanation=explanation,
            reason="El hilo completa su programa.",
            consequences=consequences,
            number=number,
        )

    def _unknown_op(self, thread: SimThread, op: MicroOp, number: int) -> Event:
        thread.advance()
        return self._emit(
            EventType.HILO_TRABAJA,
            thread=thread,
            explanation=f"Operación desconocida {op.op} (ignorada).",
            number=number,
        )

    _HANDLERS = {
        OP_SOLICITAR: _op_solicitar,
        OP_LIBERAR: _op_liberar,
        OP_LEER_DATO: _op_leer_dato,
        OP_CALCULAR: _op_calcular,
        OP_ESCRIBIR_DATO: _op_escribir_dato,
        OP_USAR: _op_usar,
        OP_ESPERAR: _op_esperar,
        OP_ADQUIRIR: _op_adquirir,
        OP_SOLTAR: _op_soltar,
        OP_TERMINAR: _op_terminar,
    }

    # =====================================================================
    # Utilidades
    # =====================================================================
    def _wake_thread(self, tid: str) -> list[str]:
        """Despierta a un hilo bloqueado y lo reencola. Devuelve la consecuencia."""
        other = self.threads[tid]
        if other.state in (ThreadState.ESPERANDO, ThreadState.BLOQUEADO):
            other.wake()
            if tid not in self.ready_queue:
                self.ready_queue.append(tid)
            return [f"{other.label} queda desbloqueado y pasa a Listo."]
        return []

    def _emit(
        self,
        event_type: EventType,
        *,
        thread: Optional[SimThread] = None,
        prev_state: Optional[str] = None,
        post_state: Optional[str] = None,
        resource: Optional[str] = None,
        explanation: str = "",
        reason: str = "",
        consequences: Optional[list[str]] = None,
        number: Optional[int] = None,
    ) -> Event:
        return Event(
            number=number if number is not None else self.event_counter,
            type=event_type,
            thread=thread.label if thread else None,
            prev_state=prev_state,
            post_state=post_state,
            resource=resource,
            explanation=explanation,
            reason=reason,
            consequences=consequences or [],
            event_time=self.time,
        )

    # --------- detección de interbloqueo (grafo de espera) ---------
    def _detect_cycle(self) -> list[str]:
        """Busca un ciclo en el grafo hilo -> hilo (dueño del recurso que espera)."""
        waits: dict[str, str] = {}
        for res in self.exclusive.values():
            if res.owner is None:
                continue
            for waiter in res.waiting:
                waits[waiter] = res.owner

        for start in waits:
            path: list[str] = []
            node: Optional[str] = start
            while node is not None and node in waits:
                if node in path:
                    idx = path.index(node)
                    return path[idx:]
                path.append(node)
                node = waits.get(node)
        return []

    # --------- invariantes ---------
    def _enforce_invariants(self, event: Event) -> None:
        problems = self.sync.check_invariants()
        for problem in problems:
            self.warnings.append(problem)
            event.consequences.append(f"⚠ Invariante violado: {problem}")

    # =====================================================================
    # Consulta de estado
    # =====================================================================
    def snapshot(self) -> dict:
        return {
            "scenario": self.config.key,
            "title": self.config.title,
            "finished": self.finished,
            "current": self.current,
            "deadlock": self.deadlock_detected,
            "context_switches": self.context_switches,
            "event_count": self.event_counter,
            "threads": [t.to_dict() for t in self.threads.values()],
            "resource": self.resource.to_dict(),
            "sync": self.sync.snapshot(),
            "exclusive": {rid: r.to_dict() for rid, r in self.exclusive.items()},
            "warnings": list(self.warnings),
            "max_wait": dict(self.max_wait),
            "timeline": list(self.timeline),
        }

    def thread(self, tid: str) -> SimThread:
        return self.threads[tid]


class SimulationController:
    """Envuelve al motor con control de reproducción (iniciar/pausar/velocidad).

    La interfaz llama a :meth:`tick` desde un temporizador. Separar esto del
    motor permite probar pausa, reanudación y velocidad sin abrir ventanas.
    """

    # Velocidades: milisegundos entre eventos.
    SPEEDS = {"Lenta": 1200, "Normal": 700, "Rápida": 350, "Muy rápida": 120}

    def __init__(self, engine: SimulationEngine, speed_name: str = "Normal") -> None:
        self.engine = engine
        self.running = False
        self.speed_name = speed_name

    @property
    def interval_ms(self) -> int:
        return self.SPEEDS.get(self.speed_name, 700)

    def set_speed(self, speed_name: str) -> None:
        if speed_name in self.SPEEDS:
            self.speed_name = speed_name

    def play(self) -> None:
        self.running = True

    def pause(self) -> None:
        self.running = False

    def toggle(self) -> bool:
        self.running = not self.running
        return self.running

    def reset(self) -> None:
        self.running = False
        self.engine.reset()

    def step_once(self):
        self.running = False
        return self.engine.step()

    def tick(self):
        """Avanza un evento solo si está en marcha. Devuelve el evento o None."""
        if not self.running or self.engine.finished:
            if self.engine.finished:
                self.running = False
            return None
        return self.engine.step()