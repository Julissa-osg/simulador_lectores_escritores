"""Pruebas del motor y de las primitivas de sincronización."""

from src.engine import SimulationController, SimulationEngine
from src.model import SimThread, ThreadKind
from src.scenarios import find_variant
from src.sync import (
    MonitorMechanism,
    NullSync,
    POLICY_FAIR,
    POLICY_READERS_FIRST,
    Semaphore,
    SemaphoreMechanism,
)


# ---------------------------------------------------------------------------
# El motor: avance, reinicio, pausa, invariantes, registro y línea de tiempo
# ---------------------------------------------------------------------------

def test_one_event_per_step():
    engine = SimulationEngine(find_variant("race_broken"))
    before = len(engine.log)
    engine.step()
    assert len(engine.log) == before + 1, "Cada paso debe producir un solo evento."


def test_step_returns_none_when_finished():
    engine = SimulationEngine(find_variant("race_broken"))
    engine.run_until_end()
    assert engine.step() is None


def test_reset_restores_initial_state():
    engine = SimulationEngine(find_variant("race_broken"))
    engine.run_until_end()
    assert engine.resource.value == 101
    engine.reset()
    assert engine.resource.value == 100
    assert engine.event_counter == 1  # solo el evento de inicio
    assert len(engine.log) == 1
    assert engine.log.last.type.value == "SIM_INICIO"
    assert all(t.state.value == "Listo" for t in engine.threads.values())
    assert engine.deadlock_detected is False


def test_controller_pause_and_resume():
    engine = SimulationEngine(find_variant("race_broken"))
    controller = SimulationController(engine)
    assert controller.tick() is None  # en pausa
    controller.play()
    assert controller.tick() is not None
    controller.pause()
    assert controller.tick() is None
    assert controller.running is False


def test_controller_step_once_pauses():
    engine = SimulationEngine(find_variant("race_broken"))
    controller = SimulationController(engine)
    controller.play()
    controller.step_once()
    assert controller.running is False


def test_controller_reset():
    engine = SimulationEngine(find_variant("race_broken"))
    controller = SimulationController(engine)
    controller.play()
    engine.run_until_end()
    controller.reset()
    assert engine.resource.value == 100
    assert controller.running is False


def test_invariants_hold_for_synced_scenarios():
    for key in ("mutex_semaphore", "readers_first", "block_semaphore", "mutex_monitor"):
        engine = SimulationEngine(find_variant(key))
        while not engine.finished:
            engine.step()
            assert not (engine.sync.active_readers and engine.sync.active_writers)
            assert len(engine.sync.active_writers) <= 1


def test_log_is_coherent_with_final_state():
    engine = SimulationEngine(find_variant("race_broken"))
    engine.run_until_end()
    assert len(engine.log) == engine.event_counter
    assert engine.log.last is not None


def test_timeline_tracks_running_thread():
    engine = SimulationEngine(find_variant("context_round_robin"))
    engine.run_until_end()
    snapshot = engine.snapshot()
    assert snapshot["timeline"], "La línea de tiempo no debe estar vacía."
    assert snapshot["context_switches"] >= 1


# ---------------------------------------------------------------------------
# Primitivas de sincronización: semáforos y monitores
# ---------------------------------------------------------------------------

def _thread(tid, kind):
    return SimThread(tid, kind, tid, [])


def test_semaphore_wait_and_signal():
    sem = Semaphore("s", 1)
    assert sem.wait("A") is True
    assert sem.value == 0
    assert sem.wait("B") is False
    assert list(sem.blocked) == ["B"]
    assert sem.signal() == "B"  # handoff
    assert sem.value == 0


def test_semaphore_never_negative():
    sem = Semaphore("s", 1)
    sem.wait("A")
    sem.wait("B")
    sem.wait("C")
    assert sem.value == 0
    assert len(sem.blocked) == 2


def test_semaphore_mechanism_excludes_writers():
    mech = SemaphoreMechanism(POLICY_READERS_FIRST)
    w1 = _thread("E1", ThreadKind.ESCRITOR)
    w2 = _thread("E2", ThreadKind.ESCRITOR)
    assert mech.request(w1).granted is True
    assert mech.request(w2).granted is False
    assert len(mech.active_writers) == 1
    newly = mech.release(w1)
    assert "E2" in newly
    assert mech.active_writers == {"E2"}


def test_monitor_mechanism_uses_conditions():
    mech = MonitorMechanism(POLICY_READERS_FIRST)
    r = _thread("L1", ThreadKind.LECTOR)
    w = _thread("E1", ThreadKind.ESCRITOR)
    assert mech.request(r).granted is True
    assert mech.request(w).granted is False
    assert "E1" in list(mech.can_write.waiters)


def test_null_sync_allows_conflicts():
    mech = NullSync()
    a = _thread("E1", ThreadKind.ESCRITOR)
    b = _thread("E2", ThreadKind.ESCRITOR)
    assert mech.request(a).granted and mech.request(b).granted
    assert len(mech.active_writers) == 2  # la exclusión no se aplica
    assert mech.check_invariants() == []  # desactivada a propósito


def test_fair_policy_blocks_reader_behind_writer():
    mech = SemaphoreMechanism(POLICY_FAIR)
    r1 = _thread("L1", ThreadKind.LECTOR)
    w = _thread("E1", ThreadKind.ESCRITOR)
    r2 = _thread("L2", ThreadKind.LECTOR)
    assert mech.request(r1).granted is True
    assert mech.request(w).granted is False
    assert mech.request(r2).granted is False, "El lector no adelanta al escritor."
    newly = mech.release(r1)
    assert "E1" in newly
    assert "L2" not in newly