"""Check the world interface against the contract, with nothing else attached:

- processes(): between one hundred and three hundred processes, unique names, one to eight numeric fields, always the same list;
- step(): returns the same processes and fields every minute, in the same order, with numbers;
- the same seed repeats the same life (also in another OS process, with a different Python hash seed);
- different seeds give different companies;
- save and load return the same world: continuing after loading gives the same minutes as continuing without stopping;
- the null variants run, and the acts interface accepts and answers (and, in the "surdo" null variant, accepts and does not
  answer).

    python -m generators.company.check [minutes]
    python generators/company/check.py [minutes]
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

if __package__ in (None, ""):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from generators.company.world import World
else:
    from .world import World


def signature(m, minutes):
    h = hashlib.sha256()
    names = [p.name for p in m.processes()]
    for _ in range(minutes):
        v = m.step()
        assert list(v.keys()) == names, "the order of the processes changed"
        for p in names:
            h.update(json.dumps(v[p]).encode())
    return h.hexdigest()


def run_checks(minutes=2500):
    failures = []

    def expect(cond, text):
        print(("ok      " if cond else "FAILED  ") + text, flush=True)
        if not cond:
            failures.append(text)

    m = World(7)
    procs = m.processes()
    names = [p.name for p in procs]
    expect(100 <= len(procs) <= 300, f"{len(procs)} processes (between one hundred and three hundred)")
    expect(len(set(names)) == len(names), "unique names")
    expect(all(1 <= len(p.fields) <= 8 for p in procs), "each process has one to eight fields")
    expect(all(len(set(p.fields)) == len(p.fields) for p in procs), "unique fields within each process")
    expect(m.t == 0, "t starts at 0")
    v = m.step()
    expect(m.t == 1 and m.day() == 0 and m.minute_of_day() == 1 and m.day_of_week() == 0, "the first step makes minute 1 of Monday")
    expect(all(len(v[p.name]) == len(p.fields) for p in procs), "each process returns one value per field")
    expect(all(isinstance(x, float) for p in procs for x in v[p.name]), "the values are numbers (float)")
    expect([p.name for p in m.processes()] == names, "processes() does not change after stepping")

    a = signature(World(7), minutes)
    b = signature(World(7), minutes)
    expect(a == b, "the same seed repeats the same life in the same process")
    child_code = ("import sys; sys.path.insert(0, %r); from generators.company.check import signature; "
                  "from generators.company.world import World; print(signature(World(7), %d))"
                  % (os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")), minutes))
    other = subprocess.run([sys.executable, "-c", child_code], capture_output=True, text=True, env=dict(os.environ, PYTHONHASHSEED="12345"))
    expect(other.stdout.strip() == a, "the same seed repeats the same life in another process (different hash seed)")
    expect(signature(World(8), minutes) != a, "different seeds give different companies")

    ran_through = World(11)
    for _ in range(minutes):
        ran_through.step()
    continued = signature(ran_through, minutes)
    paused = World(11)
    for _ in range(minutes):
        paused.step()
    with tempfile.TemporaryDirectory() as folder:
        paused.save(folder)
        resumed = World.load(folder)
    expect(resumed.t == minutes, "load restores the clock")
    expect(signature(resumed, minutes) == continued, "save and load return the same world (the following minutes are equal)")

    for null in ("sem_defeito", "embaralhado", "sem_deriva", "surdo"):
        n = World(7, null)
        for _ in range(200):
            n.step()
        expect(n.t == 200, f"the null variant {null} runs")
    m = World(3)
    for _ in range(9 * 60):
        m.step()
    number = m.receive("operação", "pergunta", "como está a rota de pedido?")
    expect(isinstance(number, int), "receive() returns a number")
    resp = []
    for _ in range(2 * 1440):
        m.step()
        resp += m.responses()
    expect(any(r[1] == number for r in resp), "the question was answered before the deadline")
    s = World(3, "surdo")
    for _ in range(9 * 60):
        s.step()
    s.receive("operação", "pergunta", "como está a rota de pedido?")
    resp = []
    for _ in range(1440):
        s.step()
        resp += s.responses()
    expect(resp == [], "in the surdo null variant nothing is answered")
    print("all good" if not failures else f"{len(failures)} failures")
    return not failures


if __name__ == "__main__":
    sys.exit(0 if run_checks(int(sys.argv[1]) if len(sys.argv) > 1 else 2500) else 1)
