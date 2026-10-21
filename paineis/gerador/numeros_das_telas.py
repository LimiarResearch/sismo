"""Calcula todos os números das telas de resultado do benchmark e confere as regras do cálculo contra o próprio protocolo.

Uso:
  python numeros_das_telas.py <repositório> <saida.json> [<pasta publication> <pasta lives>]

<repositório> é a raiz do código (com metrics/rows.py e results/publication/rows.json). A terceira pasta é a de publication.zip
descompactado (com synthetic/, company/ ...) e a quarta, a de lives.zip descompactado; sem elas, os números que não estão em rows.json (2.047 séries, composição
dos nulos, S3 por tipo de mudança, registros do M3) ficam de fora e a auditoria avisa.

Regras das células (as de metrics/rows.py, com uma regra de exibição a mais, marcada abaixo):
- cada método tem duas configurações; a célula mostra a melhor configuração abaixo do teto de alarme falso da linha;
- teto por linha: S1, S5 e L1 a L3 pelo alerta nos nulos sintéticos; S2 pelo log; S3 pelos dois; bases públicas pelo nulo
  combinado (treino e cópias embaralhadas; P4o e P4L4 usam o de P4); empresa pelo nulo da linha; os valores dos tetos são
  lidos de metrics/rows.py; uma configuração sem nulo medido fica elegível, como no protocolo;
- regra de exibição (não é do protocolo, que escolhe só o melhor global da linha): se a melhor configuração elegível de uma
  família vale 0 e outra configuração dela pontua, a célula mostra a que pontua, com † (não pode ganhar a linha);
- o detector leva † quando o status da linha diz que o próprio nulo passou do teto; nas linhas de limite o protocolo não aplica
  esse nulo;
- ‡ marca as células dos adaptadores com defeito nesta rodada arquivada (CJSD sem resposta: bases públicas e empresa; WATCH
  ponderado: linhas sintéticas com resposta). Esta lista é escrita à mão, a partir da leitura de competitors/methods.py.

Conferência embutida: para cada linha com concorrente, o maior valor elegível calculado aqui tem de ser o best_value que o
protocolo gravou em rows.json. Se não for, o script para.
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
from collections import Counter, defaultdict

REPO, SAIDA = sys.argv[1], sys.argv[2]
PUB = sys.argv[3] if len(sys.argv) > 3 else None
VIDAS = sys.argv[4] if len(sys.argv) > 4 else (os.path.join(PUB, "lives") if PUB else None)
abre = lambda p: open(p, encoding="utf-8")
R = json.load(abre(os.path.join(REPO, "results", "publication", "rows.json")))

# tetos, lidos do protocolo
_t = re.search(r"^CEILING_ALERT, CEILING_LOG, CEILING_PUBLIC, CEILING_COMPANY = ([\d.]+), ([\d.]+), ([\d.]+), ([\d.]+)",
               abre(os.path.join(REPO, "metrics", "rows.py")).read(), re.M)
TETO = dict(zip(("alerta", "log", "publico", "empresa"), map(float, _t.groups())))

ROW = {}
for x in R:
    c = x["row"].split()[0]
    ROW["L" + x["row"].split()[3][1] if c == "S6" else c] = x
S7 = ROW["S7"]
familia = lambda k: k.split("|")[0].split("/")[0]

FAMILIAS = ["page_hinkley", "cusum", "ewma", "adwin", "kswin", "ddm", "hddm_a", "hddm_w", "per_field_test", "cjsd", "watch", "ctm",
            "isolation_forest", "matrix_profile", "htm"]
# linhas com concorrente e sem concorrente, derivadas de rows.json
COM_CONCORRENTE = [c for c, x in ROW.items() if x.get("metric") and any(k != "detector|default" for k in x.get("per_method", {}))]
METRICA = {c: ROW[c]["metric"] for c in COM_CONCORRENTE}
DETECTOR_FORA = {c for c, x in ROW.items() if "detector's null above the ceiling" in x["status"]}
roda = lambda f, c: any(familia(k) == f for k in ROW[c]["per_method"])
DEFEITO = {("cjsd", c) for c in COM_CONCORRENTE if c[0] in "PM" and roda("cjsd", c)} | \
          {("watch", c) for c in COM_CONCORRENTE if c[0] in "SL" and roda("watch", c)}
assert set(FAMILIAS) >= {familia(k) for c in COM_CONCORRENTE for k in ROW[c]["per_method"]} - {"detector"}


def elegivel(c, k):
    if c[0] in "SL":
        n = S7["per_method"].get(k)
        if n is None:
            return True
        a = n["runs_with_alert"] / S7["n"] <= TETO["alerta"]
        g = n["runs_with_log"] / S7["n"] <= TETO["log"]
        return {"S2": g, "S3": a and g}.get(c, a)
    if c[0] == "P":
        base = "P4" if c in ("P4o", "P4L4") else c
        v = ROW[base]["info"]["null_warnings_per_1000"].get(k)
        return v is None or v <= TETO["publico"]
    v = ROW[c]["info"]["null"].get(k)
    return v is None or v <= TETO["empresa"]


def celula(c, f):
    """(valor, elegível, configuração) da família f na linha c; None quando a família não rodou nessa linha."""
    cf = [(d[METRICA[c]], k, elegivel(c, k)) for k, d in ROW[c]["per_method"].items() if familia(k) == f]
    if not cf:
        return None
    ok = [x for x in cf if x[2]]
    melhor_ok = max(ok) if ok else None
    melhor = max(cf)
    if melhor_ok is not None and (melhor_ok[0] > 0 or melhor[0] == 0):
        return melhor_ok
    return melhor


tabela = {}
for c in COM_CONCORRENTE:
    d = ROW[c]["per_method"].get("detector|default")
    linha = {"detector": None if d is None else [d[METRICA[c]], c not in DETECTOR_FORA, False]}
    for f in FAMILIAS:
        x = celula(c, f)
        linha[f] = None if x is None else [x[0], x[2], (f, c) in DEFEITO, x[1]]
    tabela[c] = linha
    # conferência com o protocolo: o melhor concorrente elegível é o best_value de rows.json
    melhor = max([d[METRICA[c]] for k, d in ROW[c]["per_method"].items() if k != "detector|default" and elegivel(c, k)], default=None)
    bv = ROW[c].get("best_value")
    assert (melhor is None and bv is None) or abs(melhor - bv) < 1e-12, f"{c}: melhor elegível {melhor} e best_value {bv}"


# tela de recursos
COMECO = {"detector", "cusum", "matrix_profile"}   # os únicos que estimam o começo da mudança (competitors/methods.py)


def quando(f):
    """'quando começou' nas linhas S1 e S2, com as mesmas configurações das células da tabela."""
    a = b = 0; todas_ok = True; usou = False
    for c in ("S1", "S2"):
        cel = tabela[c][f] if f != "detector" else None
        k = "detector|default" if f == "detector" else (cel[3] if cel else None)
        if k is None:
            continue
        p = ROW[c]["per_method"][k]
        if p["when_ok"] == 0:
            continue
        usou = True; a += p["when_ok"]; b += p["detected"]
        if f != "detector":
            todas_ok &= cel[1]
    return [a, b, todas_ok] if usou else None


def nunca_alerta(f):
    return all(v["detected"] == 0 for k, v in ROW["S1"]["per_method"].items() if familia(k) == f) and \
           all(v["runs_with_alert"] == 0 for k, v in S7["per_method"].items() if familia(k) == f)


recursos = {}
for f in ["detector"] + FAMILIAS:
    r = {}
    for col, c in (("onde", "S3"), ("alerta", "S1"), ("log", "S2"), ("incidentes", "M2")):
        r[col] = tabela[c][f][:3] if tabela[c].get(f) else None
    if f != "detector" and nunca_alerta(f):
        r["alerta"] = None
    r["quando"] = quando(f) if f in COMECO else None
    recursos[f] = r

# fatos citados nos textos das telas
P = {c: x["per_method"] for c, x in ROW.items() if "per_method" in x}
det = lambda c: P[c]["detector|default"]
nul = lambda c: ROW[c]["info"]["null_warnings_per_1000"]["detector|default"]
treino = lambda c: ROW[c]["info"]["null_by_part"]["detector|default"]["train"]
decidem = [c for c, x in ROW.items() if x["status"] == "PASSED" or x["status"].startswith("FAILED")]
passam = [c for c in decidem if ROW[c]["status"] == "PASSED"]
s5_empate = sorted({familia(k) for k, v in P["S5"].items() if k != "detector|default" and elegivel("S5", k) and v["sensitivity"] >= det("S5")["sensitivity"]})
m2_empate = sorted({familia(k) for k, v in P["M2"].items() if k != "detector|default" and elegivel("M2", k) and v["sensitivity"] >= det("M2")["sensitivity"]})
m5 = [m for m in ROW["M5"]["info"]["minutes_to_return_after_off_air"] if m]
fatos = {
    "S1": [det("S1")["f1"], ROW["S1"]["best_value"]], "S2": [det("S2")["f1"], ROW["S2"]["best_value"]],
    "S3": [det("S3")["detected"], det("S3")["events"]], "S3_adwin": P["S3"]["adwin/field|delta=1e-06"]["detected"],
    "S4a": [ROW["S4a"]["detector"], ROW["S4a"]["n"], ROW["S4a"]["null"]], "S4b": [ROW["S4b"]["detector"], ROW["S4b"]["n"], ROW["S4b"]["null"]],
    "S4c": [ROW["S4c"]["detector"], ROW["S4c"]["n"], ROW["S4c"]["null"]],
    "S5": [det("S5")["detected"], det("S5")["events"]], "S5_empate": s5_empate, "M2_empate": m2_empate,
    "S7": [int(S7["detector"]["alert"].split("/")[0]), int(S7["detector"]["log"].split("/")[0]), S7["n"]],
    "M1": [det("M1")["detected"], det("M1")["events"], round(ROW["M1"]["best_value"] * det("M1")["events"])],
    "M2": [det("M2")["detected"], det("M2")["events"]],
    "M3": [round(ROW["M3"]["detector"] * ROW["M3"]["n"]), ROW["M3"]["n"], round(ROW["M3"]["null"] * ROW["M3"]["n_null"]), ROW["M3"]["n_null"]],
    "M4": ROW["M4"]["detector"], "M5": [min(m5), max(m5), len(m5), len(ROW["M5"]["info"]["minutes_to_return_after_off_air"]), ROW["M5"]["n"]],
    "P1": [det("P1")["f1"], ROW["P1"]["best_value"], det("P1")["detected"], det("P1")["events"], det("P1")["false_per_1000"]],
    "publico_treino": [min(treino(c) for c in ("P4", "P5", "P6")), max(treino(c) for c in ("P4", "P5", "P6"))],
    "publico_combinado": [min(nul(c) for c in ("P4", "P5", "P6")), max(nul(c) for c in ("P4", "P5", "P6"))],
    "P4L4": [det("P4L4")["detected"], det("P4L4")["events"], det("P4L4")["sensitivity"], det("P4L4")["f1"], det("P4L4")["false"]],
    "L3": ROW["L3"]["best_value"],
    "veredito": {"passam": len(passam), "decidem": len(decidem),
                 "vitorias": sorted(c for c in passam if ROW[c].get("verdict") == "WON"),
                 "empates": sorted(c for c in passam if ROW[c].get("verdict") == "TIED"),
                 "nulo_ou_teto": sorted(c for c in passam if ROW[c].get("verdict") not in ("WON", "TIED"))},
    "concorrentes": len({familia(k) for c in COM_CONCORRENTE for k in P[c]} - {"detector"}),
    "tetos": TETO,
}

# números que dependem das saídas da rodada (publication.zip)
universo = None
F_S3_n = det("S3")["events"]
if PUB:
    sys.path.insert(0, REPO)
    import metrics.rows as mr
    saidas = mr.read(PUB)
    if not saidas:
        raise SystemExit(f"nenhuma saída da rodada em {PUB}: confira o caminho da pasta publication")
    nulos = [o for o in saidas if o["series"]["base"] == "synthetic" and (o["series"]["name"] in mr.NUL or o["series"]["variant"] == "shuffled")]
    por = defaultdict(list)
    for o in saidas:
        if o["series"]["base"] == "synthetic":
            por[(o["series"]["name"], o["series"]["variant"])].append(o)

    def acerto(o, k, tp):
        p = mr.count(o, k[0], k[1], tp)["per_event"][0]
        return p is not None and bool(p[2]) and set(p[2]) <= set(o["series"]["events"][0]["fields"])

    s3 = {}
    for nome, fams, tp in (("relacoes", mr.REL, "REAL"), ("entradas", mr.INP, "VIRTUAL")):
        lst = [o for f in fams for o in por.get((f, "main"), []) if o["series"]["events"] and o["series"]["events"][0]["fields"]]
        s3[nome] = [len(lst), sum(acerto(o, ("detector", "default"), tp) for o in lst), sum(acerto(o, ("adwin/field", "delta=1e-06"), tp) for o in lst)]
    # M3: registros "virou o normal novo" que contam como acerto
    from runner.company import read_truth
    vidas = defaultdict(dict)
    for o in saidas:
        if o["series"]["base"] == "company" and o["series"]["variant"] == "main":
            vidas[o["series"]["extra"]["life"]][o["series"]["extra"]["process"]] = o
    falta = [nv for nv in vidas if not os.path.exists(os.path.join(VIDAS, nv, "verdade.json"))]
    if not vidas or falta:
        raise SystemExit(f"vidas da empresa ausentes em {VIDAS}: {falta or 'nenhuma série da empresa'}")
    V = {nv: json.load(abre(os.path.join(VIDAS, nv, "verdade.json"))) for nv in vidas}
    TR = {nv: read_truth(V[nv], V[nv].get("nulo")) for nv in vidas}
    acertos = []; alvos = Counter(); acertos_grupo = Counter()
    grupo = lambda nv: "normais" if nv.startswith("normal") else ("embaralhada" if V[nv].get("nulo") == "embaralhado" else "variantes")
    for nv in vidas:
        for m in TR[nv]["regime_changes"]:
            for x in m["where"]:
                o = vidas[nv].get(x[0])
                if o is None or x[1] not in o["series"]["field_names"]:
                    continue
                j = o["series"]["field_names"].index(x[1])
                alvos[grupo(nv)] += 1
                ev = [e["t"] + 1 for e in o["detector"]["events"] if e["field"] == j and e["event"] == "became_new_normal"
                      and m["t"] <= e["t"] + 1 <= m["t"] + 15 * 1440]
                if ev:
                    acertos.append((nv, tuple(x), min(ev))); acertos_grupo[grupo(nv)] += 1
    # S4a: quantas das respostas de direção avaliadas são de campo numérico, onde a regra de rows.py conta "subiu" como certo
    s4a_num = s4a_n = 0
    for f_ in mr.INP:
        for o in por.get((f_, "main"), []):
            ev0 = o["series"]["events"][0]; v0 = set(ev0["fields"]); d0 = o["detector"]
            av = [a for a in d0["warnings"] if a[1] == "VIRTUAL" and ev0["window"][0] <= a[0] < ev0["window"][1]]
            rep_ = next((r for r in d0["reports"] if av and r["t"] == av[0][0]), None)
            for c_ in (rep_["fields"] if rep_ else []):
                if c_["field"] not in v0: continue
                if "direction" in c_: s4a_n += 1; s4a_num += 1
                elif "value" in c_: s4a_n += 1
                break
    # M2: incidentes independentes (mesma semente e começo a menos de 60 minutos contam como o mesmo)
    inc = sorted((V[nv]["semente"], i["inicio"]) for nv in vidas for i in V[nv].get("incidentes", []))
    indep = []
    for sem, ini in inc:
        if not any(sem == a and abs(ini - b) <= 60 for a, b in indep): indep.append((sem, ini))
    universo = {
        "s4a": [s4a_num, s4a_n], "m2_incidentes": [len(inc), len(indep)],
        "m3_alvos": {g: [alvos[g], acertos_grupo[g]] for g in ("normais", "variantes", "embaralhada")},
        "series": len(saidas),
        "s7": [sum(1 for o in nulos if o["series"]["variant"] != "shuffled"), sum(1 for o in nulos if o["series"]["variant"] == "shuffled")],
        "s3_por_tipo": s3,
        "m3": {"acertos": len(acertos), "registros_por_vida": len(set(acertos)), "registros_por_rota_minuto": len({(x, t) for _, x, t in acertos}),
               "lista": sorted(set(acertos))},
    }
    # conferências cruzadas com rows.json: o universo tem de fechar com as linhas
    assert universo["s7"][0] + universo["s7"][1] == S7["n"], "S7: nulos e embaralhadas não somam o n da linha"
    assert s3["relacoes"][0] + s3["entradas"][0] == F_S3_n, "S3: relações e entradas não somam os eventos da linha"
    assert s3["relacoes"][1] + s3["entradas"][1] == det("S3")["detected"], "S3: acertos por tipo não somam os da linha"
    assert len(acertos) == fatos["M3"][0] and sum(alvos.values()) == fatos["M3"][1], "M3: acertos ou alvos não batem com a linha"
    assert s4a_n == ROW["S4a"]["n"], "S4a: número de respostas não bate com a linha"
    assert len(inc) == fatos["M2"][1], "M2: incidentes não batem com a linha"
    fatos["S3_capacidade"] = [c for c in fatos["veredito"]["vitorias"] if c == "S3" and s3["relacoes"][2] == 0]

out = {"tabela": tabela, "recursos": recursos, "fatos": fatos, "universo": universo, "metrica": METRICA,
       "detector_fora": sorted(DETECTOR_FORA), "defeito": sorted(map(list, DEFEITO))}
json.dump(out, open(SAIDA, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1, default=list)
print("ok:", len(COM_CONCORRENTE), "linhas com concorrente; best_value conferido em todas;",
      "universo calculado" if universo else "sem as saídas da rodada: universo não calculado")
