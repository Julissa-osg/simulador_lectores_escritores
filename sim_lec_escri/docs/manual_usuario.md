# Manual de usuario

SimOS Lab se abre en una ventana con una **barra lateral** de navegación y un
**área de contenido**. Cada pantalla responde a tres preguntas: *¿Qué está
pasando?*, *¿Por qué?* y *¿Qué se puede hacer?*

## 1. Inicio

Pantalla de bienvenida con una ilustración invernal y una introducción breve.
Botones:

- **Comenzar simulación** → abre el simulador.
- **Guía de uso** → abre la introducción educativa.
- **Modo de estudio** → abre las preguntas de repaso.

## 2. Introducción

Explica el problema con la analogía de la biblioteca: qué es un lector, un
escritor, el recurso compartido y qué puede fallar. El botón **Iniciar
simulación** salta al simulador.

## 3. Simulador (pantalla principal)

### Selección
- **Escenario**: elige el grupo A–G (carrera, exclusión, lectores, inanición,
  bloqueo, interbloqueo, cambio de contexto).
- **Variante / mecanismo**: elige la variante concreta (por ejemplo, *sin
  sincronización* vs *con sincronización*, o *semáforo* vs *monitor*).

### Controles
| Botón | Acción |
| --- | --- |
| **Iniciar** | Reproduce automáticamente. |
| **Pausar / Reanudar** | Detiene o continúa la reproducción. |
| **Un paso** | Ejecuta exactamente **un** evento y pausa. |
| **Reiniciar** | Vuelve al estado inicial del escenario. |
| **Velocidad** | Lenta, Normal, Rápida o Muy rápida. |
| **Mostrar explicaciones** | Muestra/oculta el panel de explicación. |

### Qué se ve
- **Tarjetas de hilos**: lectores a la izquierda, escritores a la derecha. El
  color indica el estado y también aparece la palabra del estado.
- **Catálogo** en el centro: valor actual, valor esperado, lectores y
  escritores activos. El borde cambia según el estado (disponible, lectura
  compartida, sección crítica).
- **Cola de espera** bajo el catálogo.
- **Línea de tiempo** abajo: qué hilo tuvo la CPU en cada evento.
- En el escenario de **interbloqueo** se dibuja el grafo de asignación de
  recursos con flechas de asignación y de solicitud.

### Panel de estado
Muestra mecanismo, política, número de evento, valor del recurso, si es
consistente, lectores/escritores activos, cola, cambios de contexto y si hay
interbloqueo.

### Registro de eventos
Lista cronológica con explicación sencilla. Dos filtros: por **hilo** y por
**tipo de evento**. Se limpia al reiniciar o cambiar de escenario.

## 4. Comparar

Ejecuta el mismo escenario con cuatro enfoques (sin sincronización, semáforos,
monitores y cola justa) y muestra una tabla de métricas: resultado del contador,
coherencia, lectores y escritores atendidos, eventos, bloqueos, mayor espera,
inanición, interbloqueo y cambios de contexto.

> Las métricas son **del modelo**, no del rendimiento de un sistema real.

## 5. Modo de estudio

Preguntas de opción múltiple. Al responder, la opción correcta se marca en verde,
la incorrecta en rojo y aparece la **explicación** completa. El contador de
aciertos se actualiza; **Reiniciar respuestas** borra las respuestas.

## Consejos de uso en clase

1. Empieza por el **Escenario A** sin sincronización y ejecuta con *Un paso*.
2. Señala cómo el contador queda en 101 y lee el registro.
3. Cambia a la variante protegida y repite: 102.
4. Pasa al **Escenario D** y compara la espera del escritor entre variantes.
5. Termina con **F** (interbloqueo) y su prevención por orden global.
