"""The simulated company in the benchmark: generate a life (the world of generators/company, through its contract), read the minutes,
the processes and the truth, and say where (which field) each item of the truth should show up.

Clock: row k of the minutes matrix (counted from 0) is minute k + 1; the instants of the truth are minutes. The warnings of the
methods are item indices and become minutes by adding 1.
Where each item of the truth should show up, and the resolution of each field:
- a defective release that shows up as an exception: the error field of the first route of the affected component (and, as
  alternatives, those of the other routes of the component); then the tickets of the component (new, escalated, open);
- a release without a defect: the error field of the order route (only for the null);
- incident: the availability probe (failed checks in the minute), the errors of the order route and the new tickets of Support;
- regime change: the mean latency of each route that the change hits, with the direction given by the mean latency of the seven
  days before and after;
- drift: active customers of the portfolio, going up (none in the no-drift null);
- resolution of each field by its name: "em %" 0.5; "em horas" 0.1; anything else 1.0.
Process names, field names and the keys of the files written by the generator are data of the simulated company and stay as the
generator writes them."""
import gzip
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from runner.series import Series  # noqa: E402

ERROR_FIELD = "respostas com erro no minuto"; LATENCY_FIELD = "latência média em ms"


def resolution_of(field):
    c = field.lower()
    if "em %" in c:
        return 0.5
    if "em horas" in c:
        return 0.1
    return 1.0


def generate(folder, days, seed, null=None, python=sys.executable):
    """One life of the company, written by generators/company/run.py (minutos.csv.gz, processos.json, verdade.json)."""
    if os.path.exists(os.path.join(folder, "verdade.json")):
        return folder
    os.makedirs(folder, exist_ok=True)
    cmd = [python, "-m", "generators.company.run", folder, str(days), str(seed)] + ([null] if null else [])
    subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    return folder


def read(folder):
    procs = json.load(open(os.path.join(folder, "processos.json"), encoding="utf-8"))
    with gzip.open(os.path.join(folder, "minutos.csv.gz"), "rt", encoding="utf-8") as f:
        f.readline(); M = np.loadtxt(f, delimiter=",", ndmin=2)
    columns, k = {}, 0
    for p in procs:
        for c in p["campos"]:
            columns[(p["nome"], c)] = k; k += 1
    assert k == M.shape[1], (k, M.shape)
    return procs, M, columns, json.load(open(os.path.join(folder, "verdade.json"), encoding="utf-8"))


def read_truth(v, null):
    """The truth of a life (verdade.json) turned into what the rows score: releases, incidents, regime changes and drift, each with
    the fields where it should show up ([process, field])."""
    from generators.company.catalog import COMPONENT_NAME, ROUTE_COMPONENT, ROUTE_NAME
    route = lambda r: "rota " + ROUTE_NAME.get(r, r); comp = lambda c: COMPONENT_NAME.get(c, c)
    episodes = {}
    for e in v.get("episodios_de_defeito_no_ar", []):
        episodes.setdefault(e.get("liberado_em"), []).append(e)
    releases = []
    for L in v.get("liberacoes", []):
        eps = [e for e in episodes.get(L["t"], []) if e.get("como_aparece") == "exceção"]
        if eps:
            e = min(eps, key=lambda e: e.get("primeiro_erro") or 10 ** 9); c = e["componente"]
            routes = [r for r, cc in ROUTE_COMPONENT.items() if cc == c]; r0 = routes[0] if routes else c
            pe, pc, ps = e.get("primeiro_erro"), e.get("primeiro_chamado"), e.get("primeira_escalacao")
            releases.append({"t": L["t"], "defect": True,
                             "where": [[route(r0), ERROR_FIELD], ["chamados de " + comp(c), "novos no minuto"], ["chamados de " + comp(c), "escalados"],
                                       ["chamados de " + comp(c), "abertos"]],
                             "alternatives": [[route(r), ERROR_FIELD] for r in routes],
                             "delays": [max(1, (pc - pe) if pc and pe else 20), max(1, (ps - pc) if ps and pc else 20), 1],
                             "first_error": pe, "off_air": e.get("saiu_do_ar"), "component": c})
        else:
            releases.append({"t": L["t"], "defect": False, "where": [["rota pedido", ERROR_FIELD]]})
    incidents = [{"start": i["inicio"], "end": i["fim"], "where": [["sonda de disponibilidade", "verificações com falha no minuto"], ["rota pedido", ERROR_FIELD],
                                                                   ["projeto Suporte: movimento", "chamados novos no minuto"]]}
                 for i in v.get("incidentes", [])]
    changes = []
    for m in v.get("mudancas_de_regime", []):
        before = sum(x for x in (m.get("latencia_media_7_dias_antes") or [0]) if x is not None)
        after = sum(x for x in (m.get("latencia_media_7_dias_depois") or [0]) if x is not None)
        changes.append({"t": m["t"], "where": [[route(r), LATENCY_FIELD] for r in m.get("rotas", [])], "direction": "up" if after >= before else "down"})
    drift = None if null == "sem_deriva" else {"where": [["carteira de clientes", "clientes ativos"]], "direction": "up"}
    return {"releases": releases, "incidents": incidents, "regime_changes": changes, "drift": drift}


def series(folder, part, life, warmup=2000):
    """One series per process (the monitor of each process is one part), without a response, one item per minute."""
    procs, M, columns, _ = read(folder); out = []
    for p in procs:
        cols = [columns[(p["nome"], c)] for c in p["campos"]]
        out.append(Series(base="company", name=f"{life}|{p['nome']}", part=part, X=M[:, cols].astype(float), warmup=warmup,
                          score_start=warmup, minutes_per_item=1.0, field_names=list(p["campos"]), resolution=[resolution_of(c) for c in p["campos"]],
                          extra={"process": p["nome"], "columns": cols, "life": life}))
    return out
