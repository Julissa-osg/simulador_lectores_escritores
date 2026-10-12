# Manual técnico

## 1. Arquitectura y flujo

Ver [arquitectura.md](arquitectura.md). Resumen del flujo:

1. `main.py` crea `MainWindow`.
2. `SimulatorView` construye un `SimulationEngine` desde un `ScenarioConfig`.
3. Un `SimulationController` gestiona play/pause/step/reset y la velocidad.
4. Un temporizador (`after`) llama a `controller.tick()` → `engine.step()`.
5. Tras cada paso la vista llama a `engine.snapshot()` y redibuja el Canvas.

## 2. Modelo de eventos

`Event` es un `dataclass` inmutable en la práctica con número, tipo, hilo,
estados, recurso, explicación, motivo y consecuencias. Se crea con
`engine._emit(...)` y se añade a `EventLog`. **Un paso = un evento**; los
desbloqueos colaterales van en `consequences`.

## 3. Modelo de hilos

`SimThread` contiene `program: list[MicroOp]` y `pc`. El motor interpreta la
micro-operación `program[pc]`:

| Operación | Efecto |
| --- | --- |
| `SOLICITAR` | pide acceso; entra o se bloquea |
| `LIBERAR` | libera acceso |
| `LEER_DATO` | copia el valor a `local_value` |
| `CALCULAR` | `local_value += arg` |
| `ESCRIBIR_DATO` | vuelca `local_value` al recurso |
| `USAR` | trabajo en la sección crítica |
| `ESPERAR` | trabajo fuera del recurso |
| `ADQUIRIR` / `SOLTAR` | recursos exclusivos (deadlock) |
| `TERMINAR` | fin del hilo; libera lo que tuviera |

Los manejadores son métodos `_op_*` y se despachan con el diccionario
`_HANDLERS`.

## 4. Recurso compartido

`SharedResource.read()`, `write(new, by, event_number)`, `updates_lost` e
`is_consistent`. `ExclusiveResource` (rid, owner, waiting) se usa solo en el
escenario de interbloqueo.

## 5. Mecanismos de sincronización

### Semáforos (`sync.py`)
`Semaphore` con `value`, `blocked` y `wait`/`signal` (con handoff). El
`SemaphoreMechanism` mantiene `wrt` (valor 0 si hay escritor) y `mutex`; en este
modelo la actualización de `read_count` es atómica (simplificación documentada).

### Monitores (`sync.py`)
`Monitor` (con `lock_owner`) y `Condition` (`wait`, `signal`, `notify_all`). El
`MonitorMechanism` usa `pueden_leer` y `puede_escribir` con política
*signal-and-continue* y re-evaluación en bucle.

### Políticas (`sync.py`)
`ReadersWritersSync._dispatch()` aplica la política. `NullSync` no aplica
exclusión. `create_sync(mechanism, policy)` construye el mecanismo adecuado
(importa dentro de la función para evitar ciclos).

### Tabla comparativa

| Aspecto | Semáforo | Monitor |
| --- | --- | --- |
| Control de acceso | wait/signal manuales | el monitor lo garantiza |
| Qué hace el programador | adquirir y liberar con cuidado | declarar condiciones |
| Esperas | cola del semáforo | variables de condición |
| Ventaja | flexible, bajo nivel | menos errores, más claro |
| Riesgo | olvidar signal, orden erróneo | condiciones mal comprobadas |
| En lectores/escritores | wrt + read_count | pueden_leer / puede_escribir |

## 6. Escenarios

Ver [escenarios.md](escenarios.md). Se definen en `scenarios.py` con
`ScenarioConfig` (con `*_factory` para poder reiniciar). `SCENARIO_GROUPS`
agrupa variantes para la interfaz.

## 7. Validaciones e invariantes

- `sync.check_invariants()`: no lectores+escritores a la vez, ≤ 1 escritor.
- `_enforce_invariants` añade advertencias al evento y a `warnings`.
- El modo nulo desactiva a propósito los invariantes (para mostrar la carrera).
- La detección de interbloqueo es por **ciclo en el grafo de espera**.

## 8. Pruebas

Ver [pruebas.md](pruebas.md). Ejecuta `python -m pytest -q`.

## 9. Limitaciones del simulador

- No ejecuta hilos reales; modela estados.
- Planificador round-robin determinista.
- Métricas del modelo, no de rendimiento real.
- La actualización de `read_count` se considera atómica.
- Políticas implementadas: los clásicos (lectores primero y FIFO justa); puede
  haber otras políticas reales no incluidas.

## 10. Cómo extenderlo

1. **Nuevo escenario**: añade un `ScenarioConfig` con sus `*_factory` y súmalo a
   un `ScenarioGroup`.
2. **Nueva operación**: añade la constante en `model.py`, un manejador `_op_*`
   en `engine.py` y regístralo en `_HANDLERS`.
3. **Nueva política**: añade un método `_dispatch_*` en `ReadersWritersSync`.
4. **Nueva pregunta**: edita `QUESTIONS` (vive en `src/ui/study_view.py`).
