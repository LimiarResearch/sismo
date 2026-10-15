"""Look at a recording made by run.py against its ground truth, with simple numbers, to check by eye what the world contains:

- the daily and weekly cycle (catalog requests per hour of the interface clock and per weekday), and how much each minute
  resembles the same minute one day and one week earlier (correlation);
- the customer base growing (active customers at the start, middle and end);
- each release with a defect: route errors, tickets and escalations of the component in the hour before and the hours after;
- each incident: failed requests and new tickets before, during and after;
- each regime change: the route latency in the days before and after.

    python -m generators.company.viewer <recording folder>
    python generators/company/viewer.py <recording folder>
"""
import csv
import gzip
import json
import os
import sys

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from generators.company.catalog import COMPONENT_NAME, ROUTE_NAME, ROUTE_COMPONENT
else:
    from .catalog import COMPONENT_NAME, ROUTE_NAME, ROUTE_COMPONENT

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def load(folder):
    with gzip.open(os.path.join(folder, "minutos.csv.gz"), "rt", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        data = np.array([[float(x) for x in line] for line in reader])
    with open(os.path.join(folder, "verdade.json"), encoding="utf-8") as f:
        truth = json.load(f)
    return header, data, truth


def series(header, data, name):
    return data[:, header.index(name)]


def window(x, t, begin, end):
    a, b = max(0, t - 1 + begin), min(len(x), t - 1 + end)
    return float(x[a:b].sum()) if b > a else 0.0


def hm(t):
    d, m = divmod(int(t), 1440)
    return f"day {d} {m // 60:02d}:{m % 60:02d}"


def view(folder):
    header, d, v = load(folder)
    n = d.shape[0]
    days = n // 1440
    print(f"{folder}: {n} minutes, {d.shape[1]} fields; null variant = {v['nulo']}")
    cat = series(header, d, "rota catálogo.requisições no minuto")
    t = np.arange(1, n + 1)
    hour = (t % 1440) // 60
    by_hour = [cat[hour == h].mean() for h in range(24)]
    print("catalog requests per hour (mean per minute):", " ".join(f"{h}h:{x:.1f}" for h, x in enumerate(by_hour)))
    ds = (t // 1440) % 7
    print("catalog requests per weekday (mean per minute):", " ".join(f"{WEEKDAYS[k]}:{cat[ds == k].mean():.1f}" for k in range(7)))
    for name, lag in (("one day", 1440), ("one week", 10080)):
        if n > lag + 1440:
            c = np.corrcoef(cat[lag:], cat[:-lag])[0, 1]
            print(f"catalog correlation with {name} earlier: {c:.2f}")
    portfolio = series(header, d, "carteira de clientes.clientes ativos")
    print(f"customer base: {portfolio[0]:.0f} at the start, {portfolio[n // 2]:.0f} in the middle, {portfolio[-1]:.0f} at the end "
          f"({100.0 * (portfolio[-1] / portfolio[0] - 1) / max(1, days / 7):.2f}% per week)")
    print("releases with a defect:")
    for ep in v["episodios_de_defeito_no_ar"]:
        t0 = ep["liberado_em"]
        comp = ep["componente"]
        comp_name = COMPONENT_NAME[comp]
        comp_tickets = series(header, d, f"chamados de {comp_name}.novos no minuto")
        routes = [ROUTE_NAME[r] for r, c in ROUTE_COMPONENT.items() if c == comp]
        if ep["como_aparece"] == "fila" or not routes:
            errors = series(header, d, "fila de trabalhos.falhas de trabalho no minuto")
        elif ep["como_aparece"] == "gravação dupla":
            errors = series(header, d, "pagamentos.pagamentos aprovados no minuto") - series(header, d, "pagamentos.pedidos pagos no minuto")
        elif ep["como_aparece"] == "memória":
            errors = series(header, d, "servidor da aplicação.reinícios do processo no minuto")
        else:
            errors = sum(series(header, d, f"rota {r}.respostas com erro no minuto") for r in routes)
        print(f"  {hm(t0)} {ep['funcao']} ({ep['como_aparece']}): signal {window(errors, t0, -60, 0):.0f} in the hour before, "
              f"{window(errors, t0, 0, 60):.0f} in the hour after; tickets for {comp_name} {window(comp_tickets, t0, -240, 0):.0f} in the 4 h before, "
              f"{window(comp_tickets, t0, 0, 240):.0f} in the 4 h after; left production at {hm(ep['saiu_do_ar']) if ep['saiu_do_ar'] else 'never'}")
    new_tickets = series(header, d, "projeto Suporte: movimento.chamados novos no minuto")
    probe = series(header, d, "sonda de disponibilidade.verificações com falha no minuto")
    for inc in v["incidentes"]:
        t0 = inc["inicio"]
        print(f"incident {hm(t0)} ({inc['causa']}, {inc.get('duracao_min')} min): probe failures {window(probe, t0, 0, 120):.0f}; "
              f"new tickets {window(new_tickets, t0, -120, 0):.0f} in the 2 h before and {window(new_tickets, t0, 0, 120):.0f} in the 2 h after")
    for r in v["mudancas_de_regime"]:
        for route, a, b in zip(r["rotas"], r["latencia_media_7_dias_antes"], r["latencia_media_7_dias_depois"]):
            print(f"regime change {hm(r['t'])}: {r['funcao']} {r['de']} -> {r['para']}; latency of {route} {a} ms before, {b} ms after")


if __name__ == "__main__":
    view(sys.argv[1])
