# Conceptos de Sistemas Operativos en SimOS Lab

Este documento explica los conceptos que el simulador representa y **dónde** se
observan. El modo de estudio de la aplicación repasa los mismos conceptos
mediante preguntas con respuesta explicada.

## Hilo y proceso

Un **proceso** es un programa en ejecución con su propia memoria. Un **hilo** es
un flujo de ejecución dentro de un proceso que comparte memoria con los demás.
En SimOS Lab cada Lector y cada Escritor es un hilo.

## Concurrencia y paralelismo

- **Concurrencia**: varias tareas progresan en el mismo intervalo, por turnos.
- **Paralelismo**: varias tareas se ejecutan literalmente a la vez.

El simulador modela concurrencia; no ejecuta en paralelo.

## Recurso compartido y sección crítica

El **catálogo** es el recurso compartido. La parte de la operación que accede a
él (leer-calcular-escribir o modificar) es la **sección crítica**: debe
ejecutarse bajo exclusión mutua.

## Condición de carrera

Ocurre cuando el resultado depende del orden de acceso sin sincronizar. En el
Escenario A, dos escritores leen 100, ambos calculan 101 y ambos escriben 101:
el contador debería ser 102 y se pierde una actualización.

## Exclusión mutua y sincronización

- **Exclusión mutua**: como máximo un hilo en la sección crítica.
- **Sincronización**: mecanismos que coordinan el acceso (semáforos, monitores,
  colas justas).

## Semáforo

Contador con operaciones atómicas `wait` (P) y `signal` (V). Si el valor es
cero, `wait` bloquea. Un semáforo binario funciona como candado (mutex); un
semáforo contador permite varios permisos.

En el simulador: `wrt` protege al escritor; `mutex` protege el contador de
lectores.

## Monitor y variable de condición

Un **monitor** encapsula el estado protegido y garantiza la exclusión mutua por
sí mismo. Una **variable de condición** permite esperar hasta que se cumpla algo.
Al reanudar hay que **volver a comprobar** la condición (`while`), porque el
estado pudo cambiar. En el modelo se usa la política *signal-and-continue*.

## Bloqueo, inanición e interbloqueo

- **Bloqueo**: esperar algo que llegará (Escenario E).
- **Inanición**: un hilo nunca progresa aunque el sistema sí (Escenario D).
- **Interbloqueo**: espera circular; nadie puede avanzar solo (Escenario F).

Confundir estos tres es el error más común. La clave:

| Concepto | ¿El sistema avanza? | ¿Se resuelve solo? |
| --- | --- | --- |
| Bloqueo | Sí | Sí, cuando llega la condición |
| Inanición | Sí (otros) | No, sin cambio de política |
| Interbloqueo | No | No, sin intervención |

## Cambio de contexto y planificador

El **planificador** elige qué hilo usa la CPU. Un **cambio de contexto** guarda y
restaura el estado al cambiar de hilo. Cambiar de hilo **no** evita una carrera:
son cosas distintas. El tiempo se mide en eventos del modelo, no en tiempo real.

## Espera activa

Repetir la comprobación en un bucle gastando CPU. El motor usa **esperas
pasivas** (colas de bloqueados), no espera activa.

## Política de equidad

Regla que evita que un hilo espere indefinidamente. La política **fair** (FIFO)
impide que un lector adelante a un escritor que llegó antes.

---

## De la simulación a la realidad

| En SimOS Lab | En un SO real (Python) |
| --- | --- |
| `Semaphore.wait/signal` | `threading.Semaphore.acquire/release` |
| Variable de condición | `threading.Condition.wait/notify` |
| Cambio de contexto del modelo | cambio de contexto del planificador del SO |
| Estados del hilo | estados internos del SO (varían por sistema) |

Las primitivas del simulador son **modelos educativos**: reproducen las reglas,
no la implementación real de Python.
