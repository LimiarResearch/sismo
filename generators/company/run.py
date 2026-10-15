"""Run the world on its own and record everything, so a life of the company can be stored and inspected.

    python -m generators.company.run <folder> <days> <seed> [null] [--acts file.csv]
    python generators/company/run.py <folder> <days> <seed> [null] [--acts file.csv]

<null> is one of the null variants: sem_defeito, embaralhado, sem_deriva, surdo (omit it, or pass "normal", for the normal
company).

Writes into the folder:
- minutos.csv.gz: one row per minute (t = 1, 2, ...), in the order of processes() and of the fields; the first row has the names
  "process.field";
- processos.json: the list of processes and fields;
- verdade.json: what the company had and when (ground truth, for the benchmark only);
- eventos_humanos.csv: what a person in the company would see happen, with the instant;
- respostas.csv and atos.csv: when an acts file is given, the acts delivered and the responses that came back, with instants;
- custo.json: machine time and memory.

The acts file has one row per act, with the header t,equipe,tipo,texto (minute, team, kind, text). The act on row t is delivered
through the interface right before the step that makes minute t, and happens in that minute."""
import csv
import gzip
import io
import json
import os
import resource
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from generators.company.world import World
else:
    from .world import World


def _fmt(v):
    if v == int(v):
        return str(int(v))
    return f"{v:.2f}".rstrip("0")


def read_acts(file_path):
    acts = {}
    with open(file_path, encoding="utf-8") as f:
        for line in csv.DictReader(f):
            acts.setdefault(int(line["t"]), []).append((line["equipe"].strip(), line["tipo"].strip(), line["texto"].strip()))
    return acts


def run(folder, days, seed, null=None, acts_file=None, verbose=True):
    os.makedirs(folder, exist_ok=True)
    start = time.time()
    m = World(seed, null)
    procs = m.processes()
    with open(os.path.join(folder, "processos.json"), "w", encoding="utf-8") as f:
        json.dump([{"nome": p.name, "campos": p.fields} for p in procs], f, ensure_ascii=False, indent=1)
    acts = read_acts(acts_file) if acts_file else {}
    delivered = []
    responses = []
    total = days * 1440
    with gzip.open(os.path.join(folder, "minutos.csv.gz"), "wt", encoding="utf-8", compresslevel=6, newline="") as output:
        output.write(",".join('"' + f"{p.name}.{c}".replace('"', "'") + '"' for p in procs for c in p.fields) + "\n")
        buf = io.StringIO()
        for i in range(total):
            next_t = m.t + 1
            for team, kind, text in acts.get(next_t, ()):
                number = m.receive(team, kind, text)
                delivered.append((next_t, number, team, kind, text))
            values = m.step()
            buf.write(",".join(_fmt(v) for p in procs for v in values[p.name]))
            buf.write("\n")
            for r in m.responses():
                responses.append(r)
            if m.t % 1440 == 0:
                output.write(buf.getvalue())
                buf = io.StringIO()
                if verbose:
                    print(f"day {m.t // 1440} of {days}: {time.time() - start:.0f} s", flush=True)
        output.write(buf.getvalue())
    with open(os.path.join(folder, "verdade.json"), "w", encoding="utf-8") as f:
        json.dump(m.truth(), f, ensure_ascii=False, indent=1)
    with open(os.path.join(folder, "eventos_humanos.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "acontecimento"])
        w.writerows(m.human_events())
    if acts_file:
        with open(os.path.join(folder, "atos.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t", "numero", "equipe", "tipo", "texto"])
            w.writerows(delivered)
        with open(os.path.join(folder, "respostas.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t", "numero", "equipe", "texto"])
            w.writerows(responses)
    seconds = time.time() - start
    cost = {"dias": days, "semente": seed, "nulo": null, "segundos": round(seconds, 1),
             "segundos_por_dia_simulado": round(seconds / days, 2),
             "memoria_maxima_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)}
    with open(os.path.join(folder, "custo.json"), "w", encoding="utf-8") as f:
        json.dump(cost, f, ensure_ascii=False, indent=1)
    return m, cost


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    acts_file = None
    if "--acts" in argv:
        acts_file = argv[argv.index("--acts") + 1]
        args.remove(acts_file)
    if len(args) < 3:
        print(__doc__)
        return 2
    folder, days, seed = args[0], int(args[1]), int(args[2])
    null = args[3] if len(args) > 3 and args[3] not in ("", "normal", "nenhum") else None
    _, cost = run(folder, days, seed, null, acts_file)
    print(json.dumps(cost, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
