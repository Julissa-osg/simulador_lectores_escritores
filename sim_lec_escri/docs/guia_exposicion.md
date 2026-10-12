# Guía de exposición y defensa (5–10 minutos)

## Guion sugerido

### 0. Apertura (30 s)
> "SimOS Lab es un simulador educativo del problema de Lectores y Escritores.
> Modela hilos, un recurso compartido y mecanismos de sincronización con una
> simulación determinista, para que las carreras se puedan reproducir y
> explicar."

### 1. El problema (1 min)
Muestra la pantalla **Introducción**. Explica la analogía de la biblioteca:
varios lectores pueden consultar el catálogo a la vez; un escritor necesita
acceso exclusivo. Sin coordinación aparecen carreras, inanición e interbloqueo.

### 2. Condición de carrera (2 min)
En el **Simulador**, escenario **A · sin sincronización**. Pulsa **Un paso**
seis veces. Señala el registro:
- Evento 1: E1 lee 100. Evento 2: E2 lee 100.
- Ambos calculan 101 y ambos escriben 101.
- El contador queda en **101**, no en 102. *"Se perdió una actualización."*

Cambia a la variante **con sincronización** y repite: ahora llega a **102**.

### 3. Mecanismos (1,5 min)
Pasa por **semáforo** y **monitor** en el escenario **B**. Explica que el
semáforo expone `wait`/`signal` y el monitor encapsula el candado con variables
de condición. Abre **Comparar** para mostrar la tabla de métricas (aclarando que
son del modelo).

### 4. Inanición (1 min)
Escenario **D · política injusta**: E1 espera mientras entran lectores. Muestra
la "mayor espera". Cambia a **cola justa**: la espera se reduce.

### 5. Interbloqueo (1,5 min)
Escenario **F · interbloqueo**: A1 retiene Impresora y pide Escáner; A2 al
contrario. El grafo muestra la espera circular. Cambia a **orden global**: no hay
ciclo y ambos terminan.

### 6. Cierre (30 s)
> "El simulador separa la lógica (motor) de la interfaz, es determinista y está
> probado con 32 pruebas. Su límite es claro: es un modelo educativo, no mide el
> rendimiento de una CPU real."

---

## Preguntas y respuestas para la defensa

**1. ¿Es una simulación o usa hilos reales?**
Es una simulación de eventos determinista. No crea hilos del SO; modela sus
estados para que las intercalaciones sean reproducibles.

**2. ¿Por qué no usaste hilos reales?**
Porque con hilos reales el orden de ejecución es no determinista y no se podría
demostrar la carrera de forma controlada.

**3. ¿Qué pasa exactamente en la condición de carrera?**
E1 y E2 leen 100 antes de que ninguno escriba. Calculan 101 por separado y ambos
escriben 101, perdiendo un incremento.

**4. ¿Cómo se soluciona?**
Protegiendo toda la secuencia leer-calcular-escribir con exclusión mutua.

**5. ¿Por qué varios lectores pueden leer a la vez?**
Porque leer no modifica el dato: no hay conflicto entre lectores.

**6. ¿Qué diferencia hay entre semáforo y monitor?**
El semáforo es una primitiva de bajo nivel con `wait`/`signal`; el monitor
encapsula el estado y las condiciones, garantizando la exclusión por sí mismo.

**7. ¿Qué es una variable de condición?**
Un objeto para esperar hasta que se cumpla una condición. Al reanudar hay que
volver a comprobarla porque el estado pudo cambiar.

**8. ¿Diferencia entre bloqueo e interbloqueo?**
El bloqueo se resuelve cuando llega la condición; el interbloqueo es una espera
circular que no termina sin intervención.

**9. ¿Cómo detectas el interbloqueo?**
Buscando un ciclo en el grafo hilo → dueño del recurso que se espera. No se basa
en cuánto tiempo lleva esperando un hilo.

**10. ¿Cómo previenes el interbloqueo en el escenario F?**
Imponiendo un orden global de adquisición: todos piden R1 antes que R2, lo que
hace imposible la espera circular.

**11. ¿Qué es la inanición y cómo la evitas?**
Un hilo que nunca progresa. Se evita con una política justa (cola FIFO) que
impide que los lectores adelanten a un escritor.

**12. ¿Por qué un cambio de contexto no arregla una carrera?**
Porque decide quién usa la CPU, no protege el dato. Hace falta sincronización
aparte.

**13. ¿Qué invariantes garantizas?**
No hay lectores y escritores a la vez, y como máximo un escritor activo. El
contador de lectores nunca es negativo.

**14. ¿Qué representa el "modo sin sincronización"?**
Un modo donde se relajan los invariantes a propósito, para poder mostrar la
carrera y la inconsistencia del recurso.

**15. ¿Cómo garantizas que el resultado sea reproducible?**
Con un planificador round-robin FIFO determinista: el mismo escenario produce
siempre la misma secuencia de eventos.

**16. ¿Cómo está separada la interfaz del motor?**
La interfaz solo lee `engine.snapshot()` y envía órdenes (`step`, `play`,
`reset`). Toda la lógica está en `engine.py` y `sync.py`.

**17. ¿Qué son las "consecuencias" de un evento?**
Cambios secundarios del mismo paso, como los hilos que se desbloquean al liberar
un recurso. Mantienen la regla "un paso = un evento".

**18. ¿Qué limitaciones tiene?**
No ejecuta hilos reales, el planificador es simplificado y las métricas son del
modelo, no de rendimiento real.

---

## Referencias verificables (documentación oficial)

- Documentación de Python sobre `threading`:
  <https://docs.python.org/3/library/threading.html>
- Documentación de CustomTkinter:
  <https://customtkinter.tomschimansky.com/documentation/>
- Documentación de pytest:
  <https://docs.pytest.org/en/stable/>
- Dijkstra, E. W. (1965), *Cooperating sequential processes* (artículo clásico
  donde se describen semáforos y el problema de lectores y escritores).
