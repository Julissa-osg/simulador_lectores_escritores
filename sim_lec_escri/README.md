# SimOS Lab

**Simulador visual y educativo del problema de Lectores y Escritores.**
Una herramienta de escritorio para entender la concurrencia, las condiciones de
carrera, la exclusión mutua, la inanición y el interbloqueo mediante escenarios
interactivos, un registro de eventos explicado y una estética de diario invernal.

> Importante: el simulador es una **simulación determinista de eventos**. Modela
> los estados de los hilos y las reglas de sincronización; **no** ejecuta hilos
> reales del sistema operativo. Esto es intencional: hace que las
> intercalaciones sean reproducibles y que la condición de carrera se pueda
> demostrar de forma controlada.

---

## 1. Objetivos

1. Representar hilos, recurso compartido, sección crítica y estados de ejecución.
2. Reproducir una condición de carrera y demostrar su corrección.
3. Explicar bloqueo, interbloqueo e inanición con escenarios reproducibles.
4. Comparar semáforos, monitores y políticas de acceso justo.
5. Aprender con explicaciones sencillas y modo de estudio.
6. Entregar código modular, pruebas automatizadas y documentación de defensa.

---

## 2. Tecnologías

- **Python 3** (probado con 3.14, funciona desde 3.10).
- **CustomTkinter** + **Tkinter Canvas** para la interfaz.
- **Módulos estándar** de Python para el motor (`dataclasses`, `collections`...).
- **pytest** para las pruebas (también compatibles con `unittest`).
- **Markdown** para la documentación.
- **Git** recomendado para control de versiones.

No requiere Internet tras la instalación, ni base de datos, ni servicios
externos. Funciona en local sin conexión.

---

## 3. Requisitos

- Python 3.10 o superior con `tkinter`.
- `pip` funcional.
- En Arch Linux, instala Tk si no lo tienes:

```bash
sudo pacman -S tk
```

`customtkinter` se instala como dependencia del proyecto, no del sistema.

---

## 4. Instalación en Arch Linux (recomendado)

### 4.1. Verificar Python y pip

```bash
python --version      # debe mostrar Python 3.x
python -m pip --version
```

### 4.2. Crear y activar el entorno virtual

```bash
cd sim_lec_escri
python -m venv .venv
source .venv/bin/activate
```

> Nunca uses `sudo pip`. Todo se instala dentro de `.venv`.

### 4.3. Instalar dependencias

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pytest      # solo si vas a ejecutar las pruebas
```

### 4.4. Ejecutar la aplicación

```bash
python main.py
```

Si no activaste el entorno, puedes lanzarlo directamente:

```bash
.venv/bin/python main.py
```

---

## 5. Ejecutar las pruebas automatizadas

```bash
# con el entorno activado
python -m pytest -q

# o sin activarlo
.venv/bin/python -m pytest -q
```

Resultado esperado:

```
32 passed in 0.0Xs
```

Las pruebas son deterministas: no usan aleatoriedad sin semilla y no dependen de
la velocidad de la máquina.

---

## 6. "Compilación" (Python es interpretado)

Python no necesita compilarse para ejecutarse. Aun así, puedes:

**a) Verificar que todo el código compila (bytecode):**

```bash
python -m compileall src main.py
```

**b) Ejecutar el intérprete en modo compilado (crea `__pycache__`):**

```bash
python -m compileall -q src
python main.py
```

**c) (Opcional) Crear un ejecutable único con PyInstaller**, si lo necesitas para
otro equipo sin Python:

```bash
python -m pip install pyinstaller
pyinstaller --noconfirm --windowed --name SimOS-Lab \
    --add-data "src:src" main.py
# El ejecutable queda en dist/SimOS-Lab/
```

---

## 7. Estructura del proyecto

```
sim_lec_escri/
├── main.py                     # punto de entrada
├── requirements.txt
├── README.md
├── conftest.py                 # hace importable el paquete src en pytest
├── .gitignore
├── src/                        # CÓDIGO PRINCIPAL (5 módulos)
│   ├── model.py                # datos: hilos, micro-operaciones, eventos,
│   │                           #   recurso compartido y registro
│   ├── sync.py                 # sincronización: semáforo, monitor y políticas
│   ├── engine.py               # motor determinista + controlador de reproducción
│   ├── scenarios.py            # escenarios A–G y sus variantes
│   └── ui/                     # INTERFAZ (sin lógica de simulación)
│       ├── theme.py            # identidad visual (colores y tipografías)
│       ├── app.py              # ventana, navegación, bienvenida e introducción
│       ├── simulator_view.py   # simulador principal (Canvas)
│       ├── comparison_view.py  # comparación de soluciones
│       └── study_view.py       # modo de estudio (preguntas)
├── tests/
│   ├── test_simulacion.py      # carrera, lectores/escritores, deadlock, inanición
│   └── test_motor.py           # motor y primitivas de sincronización
└── docs/                       # manuales y guías
```

Cómo se conecta: `main.py` abre `src/ui/app.py`; el **Simulador**
(`simulator_view.py`) construye un `SimulationEngine` (`engine.py`) con un
escenario (`scenarios.py`); el motor interpreta los hilos y micro-operaciones de
`model.py` y usa el mecanismo que construye `sync.py`. La interfaz solo lee
`engine.snapshot()` y envía órdenes (`play`, `step`, `reset`).

---

## 8. Uso rápido

1. **Inicio**: pulsa *Comenzar simulación*.
2. En el **Simulador**, elige un *Escenario* (A–G) y una *Variante / mecanismo*.
3. Usa **Un paso** para avanzar exactamente un evento, o **Iniciar** para
   reproducir; **Pausar/Reanudar** y **Reiniciar** están siempre disponibles.
4. Observa el **registro de eventos**, el panel de estado y la línea de tiempo.
5. En **Comparar**, ejecuta el mismo escenario con cuatro enfoques.
6. Practica los conceptos en **Modo de estudio**.

---

## 9. Solución de problemas habituales

| Síntoma | Causa probable | Solución |
| --- | --- | --- |
| `ModuleNotFoundError: customtkinter` | entorno virtual no activado | `source .venv/bin/activate` |
| `ModuleNotFoundError: tkinter` | falta Tk | `sudo pacman -S tk` |
| `No module named 'src'` | ejecutas desde otra carpeta | ejecuta `python main.py` desde la raíz del proyecto |
| La ventana no aparece (WSL/SSH) | sin servidor gráfico | usa un escritorio local o X11 forwarding |
| Fuentes feas o cuadros | fuente no instalada | se eligen alternativas automáticamente (`DejaVu`) |
| `pytest: command not found` | pytest no instalado | `python -m pip install pytest` |
| La ventana se ve pequeña/estirada | gestor de ventanas en mosaico | redimensiónala; el diseño es adaptable |

---

## 10. Windows (instrucciones separadas)

```powershell
py -3 -m venv .venv
.venv\Scripts\activate
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py -m pip install pytest
py main.py
py -m pytest -q
```

Tkinter viene incluido con el instalador oficial de Python en Windows; no hace
falta instalar nada aparte.

---

## 11. Documentación

- [Arquitectura](docs/arquitectura.md)
- [Conceptos](docs/conceptos.md)
- [Escenarios](docs/escenarios.md)
- [Pruebas](docs/pruebas.md)
- [Manual de usuario](docs/manual_usuario.md)
- [Manual técnico](docs/manual_tecnico.md)
- [Guía de estudio](docs/guia_estudio.md)
- [Guía de exposición y defensa](docs/guia_exposicion.md)

---

## 12. Limitaciones conocidas

- Es una **simulación de eventos**, no hilos reales. Los estados son una
  abstracción educativa.
- El planificador es **round-robin FIFO determinista**; no reproduce todas las
  políticas de un SO real.
- Las métricas (esperas, eventos, cambios de contexto) son **del modelo**, no
  mediciones de rendimiento reales.
- El mecanismo nulo ("sin sincronización") relaja a propósito los invariantes
  para poder mostrar la carrera.
