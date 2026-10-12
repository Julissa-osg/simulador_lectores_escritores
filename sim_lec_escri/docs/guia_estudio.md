# Guía de estudio: el código, módulo a módulo

El proyecto es deliberadamente pequeño: **5 módulos en `src/`** y la interfaz en
`src/ui/`. Esta guía explica cada archivo: para qué sirve, qué clases y
funciones define, qué recibe, qué produce y cómo se relaciona con los demás.
Incluye ejemplos manuales para ejecutar en el intérprete.

## Cómo practicar

Abre una terminal en la raíz del proyecto y entra en el intérprete:

```bash
source .venv/bin/activate
python
```

## 1. `src/model.py` — los datos

**Para qué sirve:** describe "qué hay" en la simulación. No contiene lógica de
decisión, solo datos con sus transiciones.

**Contenido (4 secciones):**

1. **Estados, hilos y micro-operaciones:** `ThreadState` (Listo, Ejecutando,
   Esperando, Bloqueado, Terminado), `ThreadKind` (Lector/Escritor), las
   constantes de micro-operaciones (`OP_SOLICITAR`, `OP_LEER_DATO`...),
   `MicroOp` (una acción con `op`, `arg` y `note`) y `SimThread` (con su
   programa, su `pc` y sus transiciones: `advance()`, `block()`, `wake()`...
   `wake()`...).

2. **Eventos:** `EventType` (el enum con los ~20 tipos de evento) y `Event`, la
   unidad mínima de avance con `short()` (la línea del registro) y `to_dict()`.

3. **Recurso compartido:** `SharedResource` (el catálogo: `read`, `write`,
   `is_consistent`, `updates_lost`) y `ExclusiveResource` (para el interbloqueo).

4. **Registro:** `EventLog` (guarda eventos en orden y permite filtrarlos).

**Se relaciona con:** el motor lo usa en cada paso; los escenarios lo usan para
crear hilos y el recurso.

```python
from src.model import SimThread, ThreadKind, MicroOp, EventLog, Event, EventType
t = SimThread("L1", ThreadKind.LECTOR, "Lector 1", [MicroOp("SOLICITAR")])
print(t.state, t.current_op.op)   # Listo SOLICITAR
t.advance(); print(t.pc)          # 1
```

## 2. `src/sync.py` — la sincronización

**Para qué sirve:** las reglas de admisión y las primitivas clásicas.

**Contenido (4 secciones):**

1. **Políticas y admisión:** `Policy` social (`POLICY_READERS_FIRST`, `POLICY_FAIR`),
   constantes `MECH_*`, `GrantResult` (¿entró?, motivo, otros que entraron) y la
   clase base `ReadersWritersSync` (quién lee, quién escribe, la cola de espera,
   `request()`/`release()`, `check_invariants()`, `snapshot()`). También
   `NullSync` (todos entran sin protección: demuestra la carrera).

2. **Semáforos:** la primitiva `Semaphore` (`wait`/`signal` con handoff) y
   `SemaphoreMechanism` (lectores/escritores con `wrt`, `mutex` y `read_count`,
   todos consistentes con el estado).

3. **Monitores:** la variable `Condition` (`wait`/`signal`/`notify_all`), el
   `Monitor` (con su `lock_owner`) y `MonitorMechanism` (con las condiciones
   `pueden_leer` y `puede_escribir`).

4. **Fábrica:** `create_sync(mechanism, policy)` devuelve el mecanismo que pide
   un escenario. Es el único punto donde el motor decide el mecanismo.

**Se relaciona con:** el motor llama a `sync.request/release` y a
`create_sync`; los escenarios usan las constantes `MECH_*` y `POLICY_*`.

```python
from src.sync import create_sync, POLICY_FAIR
from src.model import SimThread, ThreadKind
sync = create_sync("semaphore", POLICY_FAIR)
a = SimThread("E1", ThreadKind.ESCRITOR, "E1", [])
b = SimThread("E2", ThreadKind.ESCRITOR, "E2", [])
print(sync.request(a).granted, sync.request(b).granted)   # True False
print(sync.release(a))                                     # ['E2']
```

## 3. `src/engine.py` — el motor

**Para qué sirve:** interpreta los programas de los hilos y coordina el acceso.

**Clases y métodos clave:**

- `SimulationEngine(config)`: `reset()` (estado inicial, emite `SIM_INICIO`),
  `step()` (ejecuta EXACTAMENTE un evento; `None` al acabar), `run_until_end()`
  (para pruebas), `snapshot()` (estado completo para la interfaz), `_execute()` y
  los `_op_*` (un manejador por micro-operación, despachados por `_HANDLERS`),
  `_detect_cycle()` (interbloqueo por ciclo en el grafo de espera),
  `_enforce_invariants()`.
- `SimulationController(engine)`: play/pause/step_once/reset y `SPEEDS`
  (milisegundos entre eventos). La interfaz llama a `tick()` desde un temporizador.

**Se relaciona con:** lee `model.py` (clases de datos + operaciones), usa
`create_sync` de `sync.py` y recibe un `ScenarioConfig` de `scenarios.py`.

```python
from src.engine import SimulationEngine
from src.scenarios import find_variant
eng = SimulationEngine(find_variant("race_broken"))
while (ev := eng.step()) is not None:
    print(ev.short())
print("final:", eng.resource.value)   # 101
```

## 4. `src/scenarios.py` — los escenarios A–G

**Para qué sirve:** catálogo de escenarios. Define por cada uno: los hilos con
sus programas, el mecanismo y la política, el valor inicial/esperado y (solo en
F) los recursos exclusivos.

**Clases y funciones:** `ScenarioConfig` (la plantilla con `que_pasa`,
`por_que`, `solucion`, `teaching`, `threads_factory`, `resources_factory`...),
`ScenarioVariant`, `ScenarioGroup`, `SCENARIO_GROUPS`,
`find_variant(key)`, `get_group(key)`.

**Se relaciona con:** importa `model.py` (para construir hilos) y `sync.py`
(para las constantes `MECH_*`/`POLICY_*`). El motor se construye con un
`ScenarioConfig`; la interfaz los muestra para elegirlos.

```python
from src.scenarios import find_variant
cfg = find_variant("deadlock_broken")
print(cfg.title, cfg.sync_mechanism)   # F · Interbloqueo none
```

## 5. `src/ui/` — la interfaz

La interfaz **no contiene lógica de simulación**: solo lee `snapshot()` y envía
órdenes al controlador.

- `theme.py`: paleta, estados de color y tipografías (`title_font`, `ui_font`,
  `mono_font`). **No vista**, solo identidad visual.
- `app.py`: `MainWindow` (barra lateral + navegación), `DashboardView`
  (bienvenida), `IntroView` (analogía de la biblioteca) y `draw_winter_scene`.
- `simulator_view.py`: `SimulatorCanvas` (dibuja hilos, catálogo, cola, línea de
  tiempo y el grafo de interbloqueo) y `SimulatorView` (controles, estado,
  explicaciones «¿Qué está pasando?» y registro con filtros).
- `comparison_view.py`: `run_metrics(config)` y `ComparisonView` (misma
  escena con los cuatro enfoques en una tabla).
- `study_view.py`: `StudyView` con las 10 preguntas (viven en el propio archivo).

## Ejercicio guiado: medir la inanición

```python
from src.engine import SimulationEngine
from src.scenarios import find_variant

for key in ("starvation_broken", "starvation_fair"):
    eng = SimulationEngine(find_variant(key))
    eng.run_until_end()
    print(key, "espera de E1:", eng.max_wait["E1"])
```

## Ejercicio guiado: comprobar los invariantes

```python
from src.engine import SimulationEngine
from src.scenarios import find_variant
eng = SimulationEngine(find_variant("readers_first"))
while not eng.finished:
    eng.step()
    assert not (eng.sync.active_readers and eng.sync.active_writers)
print("invariantes conservados")
```