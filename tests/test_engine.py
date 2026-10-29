import pytest

from aperture.carriers import select
from aperture.core import OUTPUT, Observation
from aperture.engine import Aborted, Store, build_probes, execute, summarize
from aperture.oracles import ModelOracle


class Fake:
    capabilities, deterministic, max_concurrency = frozenset({OUTPUT}), False, 4
    description, fingerprint, columns = "fake", "fp", []

    def __init__(self, obeys=("tags",), fail=False):
        self.obeys, self.fail, self.calls = obeys, fail, 0

    def send(self, probe):
        self.calls += 1
        if self.fail:
            raise ConnectionError("down")
        ok = probe.carrier in self.obeys or probe.carrier == "control"
        return Observation(output=probe.canary if ok else "A summary.")

    def close(self):
        pass


def run(target, names=("tags", "fullwidth"), resume=False, **kw):
    store = Store(".aperture", "fp", resume)
    probes = list(build_probes(select(list(names)), 2, store.secret))
    execute(target, probes, store, concurrency=4, rate=1000, max_calls=kw.pop("max_calls", 100), **kw)
    return probes, store


def test_end_to_end_verdicts_and_control():
    probes, store = run(Fake())
    rows, control = summarize(probes, store.done, [ModelOracle()])
    by = {r.carrier: r for r in rows}
    assert control == "ok" and by["tags"].verdict == "EXPOSED" and by["tags"].exposed == 2
    assert by["fullwidth"].verdict == "HELD"


def test_failed_control_makes_everything_inconclusive():
    probes, store = run(Fake(obeys=()))
    store.done = {k: Observation(output="no") for k in store.done}  # even the plain control is ignored
    rows, control = summarize(probes, store.done, [ModelOracle()])
    assert control == "failed" and all(r.verdict == "INCONCLUSIVE" for r in rows)


def test_resume_skips_finished_probes_and_keeps_canaries():
    t1 = Fake()
    _, s1 = run(t1)
    t2 = Fake()
    _, s2 = run(t2, resume=True)
    assert t2.calls == 0 and s2.secret == s1.secret and len(s2.done) == len(s1.done)


def test_circuit_breaker_aborts_and_saves():
    with pytest.raises(Aborted):
        run(Fake(fail=True), breaker=3)


def test_budget_caps_calls():
    t = Fake()
    run(t, max_calls=3)
    assert t.calls == 3


def test_canaries_are_unique_per_probe():
    probes = list(build_probes(select(["*"]), 3, "s"))
    assert len({p.canary for p in probes}) == len(probes)
