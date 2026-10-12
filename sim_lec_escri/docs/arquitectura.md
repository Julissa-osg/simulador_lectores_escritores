# Arquitectura de SimOS Lab

## 1. Visión general

El proyecto se organiza en tres capas que **no se mezclan**:

```
   Interfaz (src/ui)                 sólo lee estado y envía órdenes
        │  snapshot() / step()
        ▼
   Motor (src/engine.py)             reglas, estados, eventos, invariantes
        │  request() / release()
        ▼
   Sincronización (src/sync.py)      semáforos, monitores, políticas

   Datos (src/model.py)              hilos, micro-operaciones, eventos,
                                     recurso compartido y registro
   Escenarios (src/scenarios.py)     configuración de cada caso A–G
```

La regla de oro: **la interfaz nunca decide quién entra al recurso**. Solo
dibuja lo que el motor dice y envía órdenes (`play`, `step`, `reset`).

## 2. Flujo de ejecución

```
main.py
  └─ MainWindow (ventana + barra lateral)
        └─ SimulatorView
              ├─ SimulationEngine(ScenarioConfig)   ← lee un escenario
              │      └─ create_sync(mechanism, policy)
              └─ SimulationController(engine)       ← play/pause/step/reset
```

Cada vez que el temporizador dispara (`after`), el controlador llama a
`engine.step()` si está en marcha. `step()` ejecuta **una** micro-operación y
devuelve un `Event`. Luego la vista llama a `engine.snapshot()` y redibuja.

## 3. El modelo de eventos

Un `Event` (`src/model.py`) contiene:

| Campo | Significado |
| --- | --- |
| `number` | número secuencial (1-based) |
| `type` | tipo de evento (`EventType`) |
| `thread` | hilo implicado |
| `prev_state` / `post_state` | estado antes y después |
| `resource` | recurso implicado |
| `explanation` | frase sencilla para el usuario |
| `reason` | motivo técnico |
| `consequences` | cambios secundarios (p. ej. hilos desbloqueados) |
| `context_switch_from` | hilo que tenía la CPU antes |

Cada paso produce **exactamente un evento**. Las consecuencias (por ejemplo,
varios hilos que se desbloquean al liberar) se agrupan en el mismo evento para
respetar la regla "un paso = un evento".

## 4. El modelo de hilos

`SimThread` guarda `tid`, `kind` (lector/escritor), `program` (lista de
`MicroOp`), `state`, `pc` (contador de programa), `local_value`, `waiting_since`
y `holds`.

Estados: **Listo, Ejecutando, Esperando, Bloqueado, Terminado**.

Un programa típico de lector:

```
[SOLICITAR, USAR, USAR, TERMINAR]
```

Cada micro-operación la interpreta un manejador del motor (`_op_solicitar`,
`_op_usar`, ...). Para añadir un comportamiento nuevo basta con añadir un `op`
y su manejador.

## 5. El recurso compartido

`SharedResource` guarda el valor del catálogo, su historial de cambios y el
valor esperado. `updates_lost` y `is_consistent` permiten detectar carreras sin
comparar con constantes dispersas por el código.

## 6. Sincronización

`sync.ReadersWritersSync` implementa las reglas de admisión y delega el
cálculo en `_dispatch()`. Dos políticas:

- `readers_first`: los lectores entran si no hay escritor activo (puede causar
  inanición de escritores).
- `fair`: cola FIFO estricta (evita adelantamientos).

`SemaphoreMechanism` y `MonitorMechanism` heredan esas reglas y añaden su
representación (semáforos o monitor con condiciones) para poder mostrarla en la
interfaz. `NullSync` no aplica exclusión (para demostrar carreras).

## 7. El planificador

El motor usa **round-robin FIFO determinista** sobre los hilos Listos. Al elegir
un hilo se registra en `timeline` y se cuenta un cambio de contexto si es
distinto al anterior. Esta decisión es la que hace reproducibles las carreras:
el orden de ejecución no depende de la velocidad de la máquina.

## 8. Invariantes

`sync.check_invariants()` comprueba:

- No hay lectores y escritores activos a la vez.
- Como máximo un escritor activo.

En el modo "sin sincronización" los invariantes se relajan a propósito. Las
violaciones se añaden a las consecuencias del evento y a `engine.warnings`.

## 9. Detección de interbloqueo

`engine._detect_cycle()` construye el grafo hilo → hilo (dueño del recurso que
se espera) y busca ciclos. Si hay ciclo, marca `deadlock_detected` y emite
`INTERBLOQUEO_DETECTADO`. La detección se basa en las **dependencias del
modelo**, no en tiempos de espera, así que una cola normal no se confunde con un
interbloqueo.

## 10. Decisiones de diseño y alternativas

- **Simulación de eventos en vez de hilos reales**: garantiza reproducibilidad.
  Un enfoque con hilos reales sería no determinista y haría imposible la
  demostración controlada de la carrera.
- **Un evento por paso**: facilita el avance paso a paso y la docencia.
- **Interfaz desacoplada**: permite probar el motor sin abrir ventanas.
- **Recursos vectoriales dibujados en el Canvas**: no hay dependencias de
  imágenes externas ni de Internet.
