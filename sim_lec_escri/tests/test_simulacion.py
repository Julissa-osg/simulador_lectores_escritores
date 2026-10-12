"""Pruebas de los escenarios: carrera, lectores/escritores, interbloqueo e inanición."""

from src.engine import SimulationEngine
from src.scenarios import find_variant, SCENARIO_GROUPS


# ---------------------------------------------------------------------------
# Escenario A · Condición de carrera
# ---------------------------------------------------------------------------

def test_race_broken_loses_one_update():
    engine = SimulationEngine(find_variant("race_broken"))
    engine.run_until_end()
    assert engine.resource.value == 101
    assert engine.resource.updates_lost == 1
    assert not engine.resource.is_consistent


def test_race_fixed_reaches_102():
    engine = SimulationEngine(find_variant("race_fixed"))
    engine.run_until_end()
    assert engine.resource.value == 102
    assert engine.resource.is_consistent
    assert engine.resource.updates_lost == 0


def test_race_interleaving_is_reproducible():
    """La carrera no depende de la velocidad: siempre da 101 sin protección."""
    results = []
    for _ in range(5):
        engine = SimulationEngine(find_variant("race_broken"))
        engine.run_until_end()
        results.append(engine.resource.value)
    assert results == [101] * 5


def test_fixed_scenario_serializes_writers():
    """Con protección, los escritores no se solapan en la sección crítica."""
    engine = SimulationEngine(find_variant("race_fixed"))
    while not engine.finished:
        engine.step()
        assert len(engine.sync.active_writers) <= 1


# ---------------------------------------------------------------------------
# Lectores y escritores: concurrencia y exclusión mutua
# ---------------------------------------------------------------------------

def _run_tracking(config):
    """Ejecuta el escenario y devuelve métricas de acceso observadas."""
    engine = SimulationEngine(config)
    max_readers = 0
    max_writers = 0
    incompatible = False
    while not engine.finished:
        event = engine.step()
        if event is None:
            break
        readers = len(engine.sync.active_readers)
        writers = len(engine.sync.active_writers)
        max_readers = max(max_readers, readers)
        max_writers = max(max_writers, writers)
        if readers and writers:
            incompatible = True
    return engine, max_readers, max_writers, incompatible


def test_readers_can_share_resource():
    engine, max_readers, _, _ = _run_tracking(find_variant("readers_first"))
    assert max_readers >= 2, "Al menos dos lectores deben coincidir en el tiempo."
    assert engine.resource.is_consistent


def test_reader_and_writer_are_mutually_exclusive():
    _, _, _, incompatible = _run_tracking(find_variant("readers_first"))
    assert not incompatible, "Nunca debe haber lectores y escritores a la vez."


def test_writers_are_mutually_exclusive():
    engine, _, max_writers, _ = _run_tracking(find_variant("mutex_semaphore"))
    assert max_writers <= 1


def test_reader_count_never_negative():
    engine = SimulationEngine(find_variant("readers_first"))
    while not engine.finished:
        engine.step()
        assert len(engine.sync.active_readers) >= 0
        assert engine.sync.reader_count >= 0


def test_monitor_behaves_like_semaphore():
    sem = SimulationEngine(find_variant("mutex_semaphore"))
    mon = SimulationEngine(find_variant("mutex_monitor"))
    sem.run_until_end()
    mon.run_until_end()
    assert sem.resource.value == mon.resource.value == 104


# ---------------------------------------------------------------------------
# Escenario F · Interbloqueo y su prevención
# ---------------------------------------------------------------------------

def test_deadlock_is_detected():
    engine = SimulationEngine(find_variant("deadlock_broken"))
    engine.run_until_end()
    assert engine.deadlock_detected
    blocked = [t for t in engine.threads.values() if t.state.value == "Bloqueado"]
    assert len(blocked) == 2


def test_deadlock_event_in_log():
    engine = SimulationEngine(find_variant("deadlock_broken"))
    engine.run_until_end()
    types = {e.type.value for e in engine.log}
    assert "INTERBLOQUEO_DETECTADO" in types


def test_global_order_prevents_deadlock():
    engine = SimulationEngine(find_variant("deadlock_fixed"))
    engine.run_until_end()
    assert not engine.deadlock_detected
    assert all(t.state.value == "Terminado" for t in engine.threads.values())


def test_no_false_positive_on_normal_wait():
    """Un bloqueo normal en lectores/escritores no debe marcar interbloqueo."""
    engine = SimulationEngine(find_variant("block_semaphore"))
    engine.run_until_end()
    assert not engine.deadlock_detected


# ---------------------------------------------------------------------------
# Escenario D · Inanición y política justa
# ---------------------------------------------------------------------------

def test_starvation_happens_with_unfair_policy():
    engine = SimulationEngine(find_variant("starvation_broken"))
    engine.run_until_end()
    assert engine.max_wait["E1"] >= 15, "El escritor debe esperar mucho tiempo."


def test_fair_policy_reduces_writer_wait():
    broken = SimulationEngine(find_variant("starvation_broken"))
    broken.run_until_end()
    fair = SimulationEngine(find_variant("starvation_fair"))
    fair.run_until_end()
    assert fair.max_wait["E1"] < broken.max_wait["E1"]


def test_both_policies_produce_consistent_result():
    for key in ("starvation_broken", "starvation_fair"):
        engine = SimulationEngine(find_variant(key))
        engine.run_until_end()
        assert engine.resource.value == 101
        assert engine.resource.is_consistent


# ---------------------------------------------------------------------------
# Catálogo de escenarios
# ---------------------------------------------------------------------------

def test_all_groups_have_variants():
    assert SCENARIO_GROUPS
    for group in SCENARIO_GROUPS:
        assert group.variants, f"El grupo {group.key} no tiene variantes."