# Catálogo de escenarios

Cada escenario define hilos, mecanismo, política y valor esperado. Los grupos A–G
se eligen en el desplegable **Escenario** del simulador.

## A · Condición de carrera

- **Variante "sin sincronización"**: dos escritores hacen leer → calcular →
  escribir sobre un contador que empieza en 100. Resultado: **101** (debería ser
  102). Se pierde una actualización.
- **Variante "con sincronización"**: la secuencia se protege con exclusión mutua.
  Resultado: **102**, consistente.

La intercalación es reproducible: ambos leen antes de que ninguno escriba.

## B · Exclusión mutua

Dos escritores y un lector. Un escritor entra, los demás esperan, y al liberar
entra el siguiente. Variantes: **semáforo** y **monitor**.

## C · Lectores concurrentes

Tres lectores y un escritor. Los lectores coinciden en el tiempo (se ve el
contador de lectores activos); el escritor espera a que se vacíe la sala.

## D · Inanición (starvation)

Un escritor y cinco lectores.

- **Política injusta (`readers_first`)**: los lectores siguen entrando y el
  escritor espera muchísimo (espera medida en eventos).
- **Cola justa (`fair`)**: el escritor entra en cuanto puede; su espera se
  reduce drásticamente.

## E · Bloqueo

Un escritor largo ocupa el recurso; dos lectores quedan bloqueados y se
desbloquean cuando el escritor termina. Sirve para distinguir **bloqueo** de
**interbloqueo**.

## F · Interbloqueo (deadlock)

Dos hilos y dos recursos (Impresora, Escáner).

- **Interbloqueo**: A1 toma R1 y pide R2; A2 toma R2 y pide R1. Se forma una
  espera circular y el motor la detecta.
- **Prevención**: ambos piden en orden global (R1 antes que R2). No hay ciclo.

## G · Cambio de contexto

Se alternan lectores y escritores. La línea de tiempo muestra qué hilo tiene la
CPU en cada evento y cuántos cambios de contexto hubo.

---

## Preguntas clave por escenario

| Escenario | ¿Qué pasa? | ¿Por qué? | ¿Solución? |
| --- | --- | --- | --- |
| A | El contador queda en 101 | Ambos leen 100 antes de escribir | Proteger la sección crítica |
| B | Un solo hilo dentro | Exclusión mutua | Adquirir/liberar bien |
| C | Lectores simultáneos | Leer no cambia el dato | Bloquear escritor si hay lectores |
| D | El escritor no avanza | Política admite lectores sin fin | Cola FIFO justa |
| E | Un hilo espera | Condición no cumplida aún | Se resuelve al liberar |
| F | Nadie avanza | Espera circular | Orden global de recursos |
| G | La CPU salta de hilo | Planificación | Cambio de contexto ≠ sincronización |
