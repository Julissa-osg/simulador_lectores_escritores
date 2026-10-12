"""Escenarios educativos del laboratorio de problemas.

Cada escenario define:

* los hilos y sus programas (listas de micro-operaciones),
* el mecanismo de sincronizacion y la politica,
* el valor inicial y esperado del recurso compartido,
* los recursos exclusivos (solo para el interbloqueo).

Los escenarios que tienen una version "problematica" y otra "corregida" se
ofrecen como variantes, para que el usuario pueda compararlas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .model import ExclusiveResource, MicroOp, SimThread, ThreadKind as K
from .sync import MECH_MONITOR, MECH_NONE, MECH_SEMAPHORE, POLICY_FAIR, POLICY_READERS_FIRST


@dataclass
class ScenarioConfig:
    key: str
    title: str
    subtitle: str
    description: str
    que_pasa: str
    por_que: str
    solucion: str
    teaching: list[str]
    initial_value: int
    expected_value: int
    sync_mechanism: str
    sync_policy: str
    detected: str
    threads_factory: Callable[[], list[SimThread]]
    resources_factory: Callable[[], list[ExclusiveResource]] = lambda: []
    protected: bool = False
    needs_sync: bool = True


@dataclass
class ScenarioVariant:
    key: str
    label: str
    config: ScenarioConfig


@dataclass
class ScenarioGroup:
    key: str
    title: str
    subtitle: str
    icon: str
    variants: list[ScenarioVariant] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Constructores de hilos
# ---------------------------------------------------------------------------
def _thread(tid: str, kind: K, program: list[MicroOp]) -> SimThread:
    label = ("Lector " if kind is K.LECTOR else "Escritor ") + tid[1:]
    return SimThread(tid=tid, kind=kind, label=label, program=program)


def _reader(tid: str, reads: int = 1) -> SimThread:
    program = [MicroOp("SOLICITAR")]
    program += [MicroOp("USAR", note="consulta el catálogo") for _ in range(reads)]
    program.append(MicroOp("TERMINAR"))
    return _thread(tid, K.LECTOR, program)


def _writer(tid: str, writes: int = 1) -> SimThread:
    program = [MicroOp("SOLICITAR")]
    program += [MicroOp("USAR", note="actualiza el catálogo") for _ in range(writes)]
    program.append(MicroOp("TERMINAR"))
    return _thread(tid, K.ESCRITOR, program)


# ===========================================================================
# Escenario A. Condicion de carrera
# ===========================================================================
def _race_unprotected() -> list[SimThread]:
    def prog(tid: str) -> SimThread:
        return _thread(
            tid,
            K.ESCRITOR,
            [
                MicroOp("LEER_DATO", note="paso 1: leer"),
                MicroOp("CALCULAR", arg=1, note="paso 2: sumar"),
                MicroOp("ESCRIBIR_DATO", note="paso 3: escribir"),
                MicroOp("TERMINAR"),
            ],
        )

    return [prog("E1"), prog("E2")]


def _race_protected() -> list[SimThread]:
    def prog(tid: str) -> SimThread:
        return _thread(
            tid,
            K.ESCRITOR,
            [
                MicroOp("SOLICITAR", note="pide acceso exclusivo"),
                MicroOp("LEER_DATO", note="paso 1: leer"),
                MicroOp("CALCULAR", arg=1, note="paso 2: sumar"),
                MicroOp("ESCRIBIR_DATO", note="paso 3: escribir"),
                MicroOp("TERMINAR", note="libera el acceso"),
            ],
        )

    return [prog("E1"), prog("E2")]


RACE = ScenarioGroup(
    key="race",
    title="A · Condición de carrera",
    subtitle="Dos escritores pierden una actualización",
    icon="snow",
    variants=[
        ScenarioVariant(
            "race_broken",
            "Sin sincronización (101)",
            ScenarioConfig(
                key="race_broken",
                title="A · Condición de carrera (sin protección)",
                subtitle="Dos escritores leen 100 y ambos escriben 101",
                description=(
                    "Dos escritores incrementan un contador que empieza en 100. "
                    "La operación se descompone en leer, calcular y escribir."
                ),
                que_pasa=(
                    "Los dos escritores leen 100 antes de que ninguno escriba, "
                    "así que ambos calculan 101 y ambos escriben 101."
                ),
                por_que=(
                    "La intercalación de operaciones hace que una actualización se "
                    "pise con la otra: se pierde un incremento."
                ),
                solucion=(
                    "Proteger la secuencia completa (leer-calcular-escribir) con "
                    "exclusión mutua, como en la variante con sincronización."
                ),
                teaching=[
                    "Una condición de carrera depende de la intercalación, no de la velocidad.",
                    "El contador final es 101 en lugar de 102.",
                    "Se perdió una actualización.",
                ],
                initial_value=100,
                expected_value=102,
                sync_mechanism=MECH_NONE,
                sync_policy=POLICY_READERS_FIRST,
                detected="race",
                threads_factory=_race_unprotected,
                protected=False,
                needs_sync=False,
            ),
        ),
        ScenarioVariant(
            "race_fixed",
            "Con sincronización (102)",
            ScenarioConfig(
                key="race_fixed",
                title="A · Condición de carrera (protegida)",
                subtitle="La exclusión mutua evita perder la actualización",
                description=(
                    "El mismo incremento, pero cada escritor entra en una sección "
                    "crítica protegida por un semáforo."
                ),
                que_pasa="Ahora el contador llega a 102 de forma consistente.",
                por_que=(
                    "Ningún escritor puede leer-calcular-escribir mientras otro "
                    "está en medio de la misma secuencia."
                ),
                solucion="Mantener la sección crítica correctamente delimitada.",
                teaching=[
                    "La exclusión mutua elimina la carrera.",
                    "El resultado coincide con el esperado.",
                ],
                initial_value=100,
                expected_value=102,
                sync_mechanism=MECH_SEMAPHORE,
                sync_policy=POLICY_READERS_FIRST,
                detected="race",
                threads_factory=_race_protected,
                protected=True,
            ),
        ),
    ],
)


# ===========================================================================
# Escenario B. Exclusion mutua
# ===========================================================================
def _mutex_threads() -> list[SimThread]:
    return [
        _writer("E1", writes=2),
        _writer("E2", writes=2),
        _reader("L1", reads=1),
    ]


MUTEX = ScenarioGroup(
    key="mutex",
    title="B · Exclusión mutua",
    subtitle="Un escritor usa el recurso en exclusiva",
    icon="lock",
    variants=[
        ScenarioVariant(
            "mutex_semaphore",
            "Semáforo",
            ScenarioConfig(
                key="mutex_semaphore",
                title="B · Exclusión mutua con semáforo",
                subtitle="Solo un hilo modifica el recurso a la vez",
                description=(
                    "Dos escritores y un lector compiten por el catálogo. Cada "
                    "escritor pide permiso, entra, modifica y libera."
                ),
                que_pasa=(
                    "Cuando un escritor está dentro, los demás quedan esperando en "
                    "la cola hasta que libera el recurso."
                ),
                por_que=(
                    "El semáforo garantiza que la sección crítica la ocupa un solo "
                    "hilo a la vez."
                ),
                solucion="Adquirir y liberar el permiso alrededor de toda la sección crítica.",
                teaching=[
                    "Exclusión mutua = a lo sumo un hilo dentro.",
                    "La liberación es lo que permite entrar al siguiente.",
                ],
                initial_value=100,
                expected_value=104,
                sync_mechanism=MECH_SEMAPHORE,
                sync_policy=POLICY_READERS_FIRST,
                detected="mutex",
                threads_factory=_mutex_threads,
                protected=True,
            ),
        ),
        ScenarioVariant(
            "mutex_monitor",
            "Monitor",
            ScenarioConfig(
                key="mutex_monitor",
                title="B · Exclusión mutua con monitor",
                subtitle="El propio monitor garantiza el acceso exclusivo",
                description=(
                    "La misma situación, pero el acceso lo controla un monitor con "
                    "variables de condición en lugar de un semáforo."
                ),
                que_pasa="Idéntico comportamiento: un solo hilo dentro del recurso.",
                por_que=(
                    "El monitor encapsula el candado; el programador solo declara "
                    "las condiciones."
                ),
                solucion="Esperar y señalizar sobre condiciones, comprobando en bucle.",
                teaching=[
                    "El monitor oculta el candado al programador.",
                    "Las variables de condición expresan 'esperar hasta que...'",
                ],
                initial_value=100,
                expected_value=104,
                sync_mechanism=MECH_MONITOR,
                sync_policy=POLICY_READERS_FIRST,
                detected="mutex",
                threads_factory=_mutex_threads,
                protected=True,
            ),
        ),
    ],
)


# ===========================================================================
# Escenario C. Lectores concurrentes
# ===========================================================================
def _readers_threads() -> list[SimThread]:
    return [
        _reader("L1", reads=3),
        _reader("L2", reads=3),
        _reader("L3", reads=3),
        _writer("E1", writes=1),
    ]


READERS = ScenarioGroup(
    key="readers",
    title="C · Lectores concurrentes",
    subtitle="Varios lectores comparten el recurso a la vez",
    icon="book",
    variants=[
        ScenarioVariant(
            "readers_first",
            "Prioridad a lectores",
            ScenarioConfig(
                key="readers_first",
                title="C · Lectores concurrentes (prioridad a lectores)",
                subtitle="Los lectores entran mientras no haya un escritor activo",
                description=(
                    "Tres lectores y un escritor. Los lectores pueden coexistir; el "
                    "escritor necesita el recurso para él solo."
                ),
                que_pasa=(
                    "Varios lectores leen al mismo tiempo; el escritor espera a que "
                    "se vacíe la sala."
                ),
                por_que=(
                    "Leer no cambia el dato, así que no hay conflicto entre lectores; "
                    "escribir sí cambia el dato y exige exclusividad."
                ),
                solucion=(
                    "Dejar entrar lectores en grupo y bloquear a todos mientras un "
                    "escritor modifica."
                ),
                teaching=[
                    "Lectores simultáneos permitidos.",
                    "Un escritor activo bloquea a los lectores.",
                    "El contador de lectores activos nunca es negativo.",
                ],
                initial_value=100,
                expected_value=101,
                sync_mechanism=MECH_SEMAPHORE,
                sync_policy=POLICY_READERS_FIRST,
                detected="readers",
                threads_factory=_readers_threads,
                protected=True,
            ),
        ),
    ],
)


# ===========================================================================
# Escenario D. Inanicion (starvation)
# ===========================================================================
def _starvation_threads() -> list[SimThread]:
    return [
        _reader("L1", reads=5),
        _writer("E1", writes=1),
        _reader("L2", reads=3),
        _reader("L3", reads=3),
        _reader("L4", reads=3),
        _reader("L5", reads=3),
    ]


def _starvation_group() -> ScenarioGroup:
    common = dict(
        description=(
            "Un escritor pide acceso, pero continuamente llegan lectores que entran "
            "antes que él. Con una política de prioridad a lectores, el escritor "
            "puede no progresar nunca."
        ),
        teaching=[
            "Inanición = un hilo espera indefinidamente sin progresar.",
            "No es lo mismo que un interbloqueo: el sistema sí avanza, pero no ese hilo.",
        ],
    )
    return ScenarioGroup(
        key="starvation",
        title="D · Inanición (starvation)",
        subtitle="Prioridad a lectores vs. cola justa",
        icon="clock",
        variants=[
            ScenarioVariant(
                "starvation_broken",
                "Política injusta (hay inanición)",
                ScenarioConfig(
                    key="starvation_broken",
                    title="D · Inanición con política injusta",
                    subtitle="Los lectores adelantan siempre al escritor",
                    **common,
                    que_pasa=(
                        "El escritor E1 espera mientras los lectores entran uno tras "
                        "otro. Su tiempo de espera crece sin parar."
                    ),
                    por_que=(
                        "La política de prioridad a lectores admite a cada lector nuevo "
                        "aunque haya un escritor esperando."
                    ),
                    solucion=(
                        "Usar una cola FIFO justa, que impida a los lectores adelantar "
                        "al escritor que llegó antes."
                    ),
                    expected_value=101,
                    sync_mechanism=MECH_SEMAPHORE,
                    sync_policy=POLICY_READERS_FIRST,
                    detected="starvation",
                    threads_factory=_starvation_threads,
                    initial_value=100,
                    protected=False,
                ),
            ),
            ScenarioVariant(
                "starvation_fair",
                "Cola justa (se reduce)",
                ScenarioConfig(
                    key="starvation_fair",
                    title="D · Inanición corregida con cola justa",
                    subtitle="El escritor entra en cuanto puede",
                    **common,
                    que_pasa=(
                        "Con la cola FIFO, los lectores que llegan detrás del escritor "
                        "esperan; el escritor entra pronto."
                    ),
                    por_que=(
                        "La cola respeta el orden de llegada, así que el escritor no "
                        "puede ser adelantado para siempre."
                    ),
                    solucion="Política justa basada en el orden de las solicitudes.",
                    expected_value=101,
                    sync_mechanism=MECH_SEMAPHORE,
                    sync_policy=POLICY_FAIR,
                    detected="starvation",
                    threads_factory=_starvation_threads,
                    initial_value=100,
                    protected=True,
                ),
            ),
        ],
    )


STARVATION = _starvation_group()


# ===========================================================================
# Escenario E. Bloqueo
# ===========================================================================
def _block_threads() -> list[SimThread]:
    return [
        _writer("E1", writes=3),
        _reader("L1", reads=1),
        _reader("L2", reads=1),
    ]


BLOCK = ScenarioGroup(
    key="block",
    title="E · Bloqueo",
    subtitle="Un hilo espera una condición que no se cumple",
    icon="hourglass",
    variants=[
        ScenarioVariant(
            "block_semaphore",
            "Espera normal",
            ScenarioConfig(
                key="block_semaphore",
                title="E · Bloqueo normal",
                subtitle="Esperar no es lo mismo que interbloquearse",
                description=(
                    "Un escritor largo ocupa el recurso; los lectores que llegan quedan "
                    "bloqueados hasta que el escritor libere."
                ),
                que_pasa=(
                    "Los lectores L1 y L2 esperan porque E1 está modificando el catálogo."
                ),
                por_que="Un lector no puede leer mientras un escritor modifica el dato.",
                solucion=(
                    "El bloqueo se resuelve solo: cuando E1 libera, los lectores entran."
                ),
                teaching=[
                    "Bloqueado = esperando una condición que puede llegar.",
                    "Interbloqueado = esperando algo que nunca llegará sin intervención.",
                ],
                initial_value=100,
                expected_value=103,
                sync_mechanism=MECH_SEMAPHORE,
                sync_policy=POLICY_READERS_FIRST,
                detected="block",
                threads_factory=_block_threads,
                protected=True,
            ),
        ),
    ],
)


# ===========================================================================
# Escenario F. Interbloqueo (deadlock)
# ===========================================================================
def _deadlock_threads() -> list[SimThread]:
    def prog(tid, first, second):
        return _thread(
            tid,
            K.ESCRITOR,
            [
                MicroOp("ADQUIRIR", arg=first, note="toma el primer recurso"),
                MicroOp("ADQUIRIR", arg=second, note="pide el segundo recurso"),
                MicroOp("SOLTAR", arg=second),
                MicroOp("SOLTAR", arg=first),
                MicroOp("TERMINAR"),
            ],
        )

    return [prog("A1", "R1", "R2"), prog("A2", "R2", "R1")]


def _deadlock_fixed_threads() -> list[SimThread]:
    def prog(tid):
        return _thread(
            tid,
            K.ESCRITOR,
            [
                MicroOp("ADQUIRIR", arg="R1", note="siempre R1 primero"),
                MicroOp("ADQUIRIR", arg="R2", note="y después R2"),
                MicroOp("SOLTAR", arg="R2"),
                MicroOp("SOLTAR", arg="R1"),
                MicroOp("TERMINAR"),
            ],
        )

    return [prog("A1"), prog("A2")]


def _deadlock_resources() -> list[ExclusiveResource]:
    return [ExclusiveResource("R1", "Impresora"), ExclusiveResource("R2", "Escáner")]


DEADLOCK = ScenarioGroup(
    key="deadlock",
    title="F · Interbloqueo (deadlock)",
    subtitle="Espera circular entre dos hilos y dos recursos",
    icon="cycle",
    variants=[
        ScenarioVariant(
            "deadlock_broken",
            "Interbloqueo (se cuelga)",
            ScenarioConfig(
                key="deadlock_broken",
                title="F · Interbloqueo",
                subtitle="A1 toma R1 y pide R2; A2 toma R2 y pide R1",
                description=(
                    "Dos hilos toman recursos en orden opuesto. Cada uno retiene uno y "
                    "pide el que tiene el otro."
                ),
                que_pasa=(
                    "A1 retiene la Impresora y espera el Escáner; A2 retiene el Escáner "
                    "y espera la Impresora. Nadie puede continuar."
                ),
                por_que="Hay una espera circular: hilo → recurso → hilo → recurso.",
                solucion=(
                    "Romper la espera circular: pedir todos los recursos en un orden "
                    "global fijo (primero R1, después R2)."
                ),
                teaching=[
                    "Interbloqueo = espera circular de recursos.",
                    "Ninguno puede avanzar por sí solo.",
                ],
                initial_value=100,
                expected_value=100,
                sync_mechanism=MECH_NONE,
                sync_policy=POLICY_READERS_FIRST,
                detected="deadlock",
                threads_factory=_deadlock_threads,
                resources_factory=_deadlock_resources,
                protected=False,
                needs_sync=False,
            ),
        ),
        ScenarioVariant(
            "deadlock_fixed",
            "Prevención (orden global)",
            ScenarioConfig(
                key="deadlock_fixed",
                title="F · Prevención del interbloqueo",
                subtitle="Ambos hilos piden los recursos en el mismo orden",
                description=(
                    "Los dos hilos adquieren primero R1 y luego R2. Es imposible que se "
                    "forme un ciclo de espera."
                ),
                que_pasa="Uno espera al otro, pero ese otro puede terminar y liberarlo.",
                por_que="Sin espera circular no puede haber interbloqueo.",
                solucion="Orden global de adquisición de recursos.",
                teaching=[
                    "Prevención: imponer un orden total a los recursos.",
                    "El bloqueo que queda es normal y se resuelve solo.",
                ],
                initial_value=100,
                expected_value=100,
                sync_mechanism=MECH_NONE,
                sync_policy=POLICY_READERS_FIRST,
                detected="deadlock",
                threads_factory=_deadlock_fixed_threads,
                resources_factory=_deadlock_resources,
                protected=True,
                needs_sync=False,
            ),
        ),
    ],
)


# ===========================================================================
# Escenario G. Cambio de contexto
# ===========================================================================
def _context_threads() -> list[SimThread]:
    return [
        _reader("L1", reads=2),
        _writer("E1", writes=1),
        _reader("L2", reads=2),
    ]


CONTEXT = ScenarioGroup(
    key="context",
    title="G · Cambio de contexto",
    subtitle="La CPU salta de un hilo a otro",
    icon="arrows",
    variants=[
        ScenarioVariant(
            "context_round_robin",
            "Round-robin",
            ScenarioConfig(
                key="context_round_robin",
                title="G · Cambio de contexto",
                subtitle="La línea de tiempo muestra qué hilo tiene la CPU",
                description=(
                    "El planificador reparte la CPU entre los hilos. Cada cambio "
                    "guarda el estado del hilo saliente y restaura el del entrante."
                ),
                que_pasa=(
                    "La línea de tiempo alterna L1, E1 y L2. Cuando un hilo se bloquea, "
                    "el planificador elige otro."
                ),
                por_que=(
                    "Un cambio de contexto es guardar/restaurar el estado de ejecución, "
                    "no una forma de sincronización."
                ),
                solucion=(
                    "Cambiar de hilo reparte la CPU, pero no evita carreras: se necesita "
                    "sincronización aparte."
                ),
                teaching=[
                    "Cambio de contexto ≠ sincronización.",
                    "La línea de tiempo es del modelo educativo, no mide la CPU real.",
                ],
                initial_value=100,
                expected_value=101,
                sync_mechanism=MECH_SEMAPHORE,
                sync_policy=POLICY_READERS_FIRST,
                detected="context",
                threads_factory=_context_threads,
                protected=True,
            ),
        ),
    ],
)


SCENARIO_GROUPS: list[ScenarioGroup] = [
    RACE,
    MUTEX,
    READERS,
    STARVATION,
    BLOCK,
    DEADLOCK,
    CONTEXT,
]


def get_group(key: str) -> ScenarioGroup:
    for group in SCENARIO_GROUPS:
        if group.key == key:
            return group
    raise KeyError(key)


def find_variant(config_key: str) -> ScenarioConfig:
    for group in SCENARIO_GROUPS:
        for variant in group.variants:
            if variant.config.key == config_key:
                return variant.config
    raise KeyError(config_key)


def default_config() -> ScenarioConfig:
    return RACE.variants[0].config
