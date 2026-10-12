# Pruebas automatizadas

## Cómo ejecutarlas

```bash
source .venv/bin/activate
python -m pytest -q
```

o sin activar el entorno:

```bash
.venv/bin/python -m pytest -q
```

Resultado esperado: `32 passed`. Las pruebas son deterministas (no hay
aleatoriedad sin semilla).

## Qué cubre cada archivo

### `tests/test_simulacion.py` (escenarios)

**Carrera:**
1. La carrera deja el contador en **101** (se pierde una actualización).
2. Con protección llega a **102** y es consistente.
3. La intercalación es reproducible (se repite 5 veces → siempre 101).
4. No se solapan dos escritores en la variante protegida.

**Lectores y escritores:**
5. Varios lectores coinciden (lectura concurrente permitida).
6. Nunca hay lectores y escritores a la vez.
7. Los escritores son mutuamente excluyentes.
8. El contador de lectores nunca es negativo.
9. El monitor y el semáforo producen el mismo resultado.

**Interbloqueo:**
10. Se detecta el interbloqueo del Escenario F.
11. Aparece el evento `INTERBLOQUEO_DETECTADO` en el registro.
12. El orden global lo previene y ambos hilos terminan.
13. Un bloqueo normal no genera un falso interbloqueo.

**Inanición:**
14. La política injusta produce inanición (espera ≥ 15 eventos).
15. La política justa reduce la espera del escritor.
16. Ambas políticas dan un resultado consistente.

**Catálogo:**
17. Todos los grupos de escenarios tienen variantes.

### `tests/test_motor.py` (motor y sincronización)

18. Un paso produce exactamente un evento.
19. `step()` devuelve `None` al terminar.
20. El reinicio restaura recursos, contadores y registro.
21. Pausa y reanudación del controlador.
22. `step_once` deja la simulación en pausa.
23. El reinicio del controlador deja de reproducir.
24. Los invariantes se conservan en los escenarios sincronizados.
25. El registro es coherente con el estado final.
26. La línea de tiempo registra los cambios de contexto.
27. `wait`/`signal` de semáforo se comportan correctamente (con handoff).
28. El valor del semáforo nunca es negativo.
29. El mecanismo de semáforos excluye escritores.
30. El monitor usa variables de condición.
31. Sin sincronización se permite el conflicto (a propósito).
32. La cola justa impide que un lector adelante a un escritor.

## Cómo interpretar los resultados

- `passed`: prueba superada.
- `FAILED`: mira la línea concreta; el mensaje indica qué se esperaba.
- Si cambias el motor, vuelve a ejecutar **todas** las pruebas, no solo una.

## Añadir una prueba nueva

```python
from src.engine import SimulationEngine
from src.scenarios import find_variant

def test_mi_caso():
    engine = SimulationEngine(find_variant("race_broken"))
    engine.run_until_end()
    assert engine.resource.value == 101
```
