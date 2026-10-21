"""Gera as oito telas de resultado do benchmark a partir de numeros.json, rows.json e dos arquivos do protocolo.

Uso: python telas.py <repositório> <numeros.json> <pasta de saída>

Regra: todo número visível nas telas é um valor calculado. No texto fixo (os moldes em moldes/ e as frases deste script) não
há número escrito à mão: cada número entra por uma chave ⟦nome⟧ ou pela função m(), e a função valores() diz de onde vem cada
chave (rows.json, numeros.json, metrics/rows.py, protocol/seeds.json ou os rótulos das linhas). Antes de gravar, o script
gera as telas de novo com cada valor calculado marcado e para em erro se sobrar no texto visível algum dígito sem marca que não
seja um identificador (códigos de linha como S1 ou P4L4, F1, sha256). As únicas constantes fora dos dados são a data da revisão
independente que achou os defeitos de adaptador e os nomes dos métodos.

A auditoria (auditoria.py) roda este gerador e compara o resultado, byte a byte, com o HTML publicado.
"""
import html as _html, json, os, re, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
abre = lambda p: open(p, encoding="utf-8")
MARCA = [False]
m = lambda s: f"\x01{s}\x02" if MARCA[0] else str(s)
LOGO = "/_blob/866a541afeb37bd7d1dc79b2ff7009cd"
DATA_REVISAO = {"en": "18 Oct 2026", "pt": "18/10/2026"}   # data da revisão independente que achou os defeitos de adaptador
IDENT = re.compile(r"^(S[1-7][a-c]?|L[1-4]|P[1-6](L4|c|o)?|M[1-5]|F1|sha256)$")


# ------------------------------------------------------------------ valores calculados
def valores(repo, N):
    R = json.load(abre(os.path.join(repo, "results", "publication", "rows.json")))
    rows_py = abre(os.path.join(repo, "metrics", "rows.py")).read()
    ROW = {}
    for x in R:
        c = x["row"].split()[0]
        ROW["L" + x["row"].split()[3][1] if c == "S6" else c] = x
    rot = lambda c, pad: re.search(pad, ROW[c]["row"]).group(1)
    F, U = N["fatos"], N["universo"]
    if U is None:
        raise SystemExit("numeros.json sem o universo: rode numeros_das_telas.py com as pastas publication e lives")
    T, V = F["tetos"], F["veredito"]
    P = {c: x["per_method"] for c, x in ROW.items() if "per_method" in x}
    det = lambda c: P[c]["detector|default"]
    m5 = F["M5"]; m4 = F["M4"]
    nulo_emb = max(ROW[c]["info"]["null_by_part"]["detector|default"]["shuffled"] for c in ("P1", "P4", "P5", "P6"))
    q, qc = N["recursos"]["detector"]["quando"], N["recursos"]["cusum"]["quando"]
    ent, rel = U["s3_por_tipo"]["entradas"], U["s3_por_tipo"]["relacoes"]
    cap = F["S3_capacidade"]
    base = {  # chave: (valor, formato)
        "series": (U["series"], "milhar"), "concorrentes": (F["concorrentes"], "int"), "linhas": (len(R), "int"),
        "hash": (json.load(abre(os.path.join(repo, "protocol", "seeds.json")))["frozen_sha256"][:8], "txt"),
        "teto_alerta": (T["alerta"], "pc"), "teto_log": (T["log"], "pc"), "teto_pub": (T["publico"], "1"), "teto_emp": (T["empresa"], "1"),
        "campos_max": (max(int(x) for x in re.findall(r"(\d+) \(", ROW["S3"]["info"]["N"])), "int"),
        "tol_dp": (float(rot("S4b", r"within ([\d.]+) sd")), "2"),
        "itens_tamanho": (int(re.search(r"tr = a\[0\] \+ (\d+)", rows_py).group(1)), "int"),
        "tol_quando": (int(re.search(r'm\["minutes_per_item"\], (\d+), m\["d"\]\)', rows_py).group(1)), "int"),
        "curto": (int(rot("P4L4", r"shorter than (\d+) items")), "int"), "campos_smd": (int(rot("P4o", r"among (\d+)")), "int"),
        "m1_min": (int(rot("M1", r"within (\d+) min")), "int"), "m2_min": (int(rot("M2", r"within (\d+) min")), "int"),
        "m3_dias": (int(rot("M3", r"within (\d+) days")), "int"), "m5_h": (int(rot("M5", r"within (\d+) min")) // 60, "int"),
        "aquec": (int(rot("P1c", r"warmup(\d+)")), "int"),
        "s1": (F["S1"][0], "3"), "s1_best": (F["S1"][1], "3"), "s2": (F["S2"][0], "3"), "s2_best": (F["S2"][1], "3"),
        "s3_k": (F["S3"][0], "int"), "s3_n": (F["S3"][1], "int"),
        "ent_k": (ent[1], "int"), "ent_n": (ent[0], "int"), "ent_adwin": (ent[2], "int"),
        "rel_k": (rel[1], "int"), "rel_n": (rel[0], "int"), "s3_total": (ent[0] + rel[0], "int"),
        "s4a_k": (round(F["S4a"][0] * F["S4a"][1]), "int"), "s4a_n": (F["S4a"][1], "int"), "s4a": (F["S4a"][0], "3"),
        "s4b_k": (round(F["S4b"][0] * F["S4b"][1]), "int"), "s4b_n": (F["S4b"][1], "int"), "s4b": (F["S4b"][0], "3"), "s4b_nulo": (F["S4b"][2], "3"),
        "s4c_k": (round(F["S4c"][0] * F["S4c"][1]), "int"), "s4c_n": (F["S4c"][1], "int"), "s4c": (F["S4c"][0], "3"),
        "s4c_nulo": (F["S4c"][2], "3"), "s4c_nulo_k": (round(F["S4c"][2] * F["S4c"][1]), "int"),
        "dir_pc": (min(F["S4a"][0], F["S4b"][0]), "pct"), "nn_pc": (F["S4c"][0], "pct"),
        "s5_k": (F["S5"][0], "int"), "s5_n": (F["S5"][1], "int"), "s5_emp": (len(F["S5_empate"]), "int"),
        "s7_alerta": (F["S7"][0], "int"), "s7_log": (F["S7"][1], "int"), "s7_n": (F["S7"][2], "int"),
        "s7_nul": (U["s7"][0], "int"), "s7_emb": (U["s7"][1], "int"),
        "m2_k": (F["M2"][0], "int"), "m2_n": (F["M2"][1], "int"),
        "m3_k": (F["M3"][0], "int"), "m3_n": (F["M3"][1], "int"), "m3": (F["M3"][0] / F["M3"][1], "3"),
        "m3_nulo_k": (F["M3"][2], "int"), "m3_nulo_n": (F["M3"][3], "int"), "m3_nulo": (F["M3"][2] / F["M3"][3], "3"),
        "m3_reg": (U["m3"]["registros_por_vida"], "int"),
        "p1": (F["P1"][0], "3"), "p1_best": (F["P1"][1], "3"), "p1_k": (F["P1"][2], "int"), "p1_n": (F["P1"][3], "int"),
        "p1_fp": (round(F["P1"][4]), "int"), "emb_zero": (nulo_emb, "g"),
        "tr_min": (F["publico_treino"][0], "1"), "tr_max": (F["publico_treino"][1], "1"),
        "cb_min": (F["publico_combinado"][0], "1"), "cb_max": (F["publico_combinado"][1], "1"),
        "m1_k": (F["M1"][0], "int"), "m1_n": (F["M1"][1], "int"), "m1_best": (F["M1"][2], "int"),
        "m4_k": (sum(1 for v in m4["normal"] if v), "int"), "m4_n": (len(m4["normal"]), "int"),
        "m4_zeros": (sum(1 for v in m4["normal"] if v == 0), "conta"), "m4_vezes": (m4["no_drift"][0], "vezes"),
        "m5_h0": (round(m5[0] / 60), "int"), "m5_h1": (round(m5[1] / 60), "int"), "m5_k": (m5[2], "int"), "m5_n": (m5[3], "int"),
        "m5": (ROW["M5"]["detector"], "3"),
        "l3": (det("L3")["f1"], "g"), "l3_best": (F["L3"], "3"),
        "p4l4_k": (F["P4L4"][0], "int"), "p4l4_n": (F["P4L4"][1], "int"), "p4l4": (F["P4L4"][2], "3"),
        "p4l4_f1": (F["P4L4"][3], "3"), "p4l4_falsos": (F["P4L4"][4], "milhar"),
        "quando_k": (q[0], "int"), "quando_n": (q[1], "int"), "cusum_k": (qc[0], "int"), "cusum_n": (qc[1], "int"),
        "passam": (V["passam"], "int"), "decidem": (V["decidem"], "int"), "vit": (len(V["vitorias"]) - len(cap), "int"),
        "cap": (len(cap), "int"), "emp": (len(V["empates"]), "int"), "nul": (len(V["nulo_ou_teto"]), "int"),
        "zero": (0, "int"),   # regra da caixa de latão nesta tabela: sem vencedor quando o maior valor permitido é 0 (função tabela)
        "m4_min": (min(m4["normal"]), "int"),
        "m4_esperado": ({"never": 0}[re.search(r"and (never) without drift", ROW["M4"]["row"]).group(1)], "int"),
        "cat_alvo": (float(re.search(r'c\["value"\] == ([\d.]+) and c\["share_after"\]', rows_py).group(1)), "g"),   # a categoria que a regra de S4a conta como certa
        "s4a_num": (U["s4a"][0], "int"), "s4a_cat": (U["s4a"][1] - U["s4a"][0], "int"),
        "s4a_sempre": ((U["s4a"][0] + (U["s4a"][1] - U["s4a"][0])) / U["s4a"][1], "3"),
        "m2_indep": (U["m2_incidentes"][1], "int"),
        "q480_det": (q[0] / (det("S1")["events"] + det("S2")["events"]), "pct"),
        "q480_cusum": (qc[0] / (det("S1")["events"] + det("S2")["events"]), "pct"),
        "q_total": (det("S1")["events"] + det("S2")["events"], "int"),
        "mil": (int(re.search(r"null\[k\] = (\d+)\.0 \* f / i", rows_py).group(1)), "milhar"),
    }
    for c in ("P1L4", "P5L4", "P6L4"):
        base[c.lower() + "_n"] = (ROW[c]["n"], "int")
    out = {}
    for lang in ("en", "pt"):
        d = {}
        for k, (v, f) in base.items():
            d[k] = fmt(v, f, lang)
        d["data"] = DATA_REVISAO[lang]
        out[lang] = d
    return out, ROW


def fmt(v, f, lang):
    dec = (lambda s: s.replace(".", ",")) if lang == "pt" else (lambda s: s)
    if f == "int": return str(int(v))
    if f == "txt": return str(v)
    if f == "milhar": s = f"{int(v):,}"; return s.replace(",", ".") if lang == "pt" else s
    if f in ("1", "2", "3"): return dec(f"{v:.{f}f}")
    if f == "pc": return f"{round(100 * v):g}%"
    if f == "pct": return "100%" if round(100 * v, 1) == 100 else dec(f"{100 * v:.1f}%")
    if f == "g": return dec(f"{v:g}")
    if f == "conta": return {"en": {1: "one", 2: "two"}, "pt": {1: "uma", 2: "duas"}}[lang].get(int(v), str(v))
    if f == "vezes": return {"en": {1: "once", 2: "twice"}, "pt": {1: "uma vez", 2: "duas vezes"}}[lang].get(int(v), str(v))
    raise ValueError(f)


def preenche(texto, VL):
    return re.sub(r"⟦([a-z0-9_]+)⟧", lambda g: m(VL[g.group(1)]), texto)


# ------------------------------------------------------------------ telas escritas como molde (placar e propósito)
def de_molde(nome, VL):
    return preenche(abre(os.path.join(AQUI, "moldes", nome + ".dc.html")).read(), VL)


# ------------------------------------------------------------------ tabela completa
COMP = ["page_hinkley", "cusum", "ewma", "adwin", "kswin", "ddm", "hddm_a", "hddm_w", "per_field_test", "cjsd", "watch", "ctm",
        "isolation_forest", "matrix_profile", "htm"]
HEAD = {
    "en": ["Page-<br>Hinkley", "CUSUM", "EWMA", "ADWIN", "KSWIN", "DDM", "HDDM<br>A", "HDDM<br>W", "Per-field<br>test", "CJSD", "WATCH", "CTM", "Isolation<br>forest", "Matrix<br>profile", "HTM"],
    "pt": ["Page-<br>Hinkley", "CUSUM", "EWMA", "ADWIN", "KSWIN", "DDM", "HDDM<br>A", "HDDM<br>W", "Teste<br>por campo", "CJSD", "WATCH", "CTM", "Isolation<br>forest", "Matrix<br>profile", "HTM"],
}
G = {"en": ["synthetic streams", "declared limits (do not decide)", "public datasets", "simulated company"],
     "pt": ["séries sintéticas", "limites declarados (não decidem)", "bases públicas", "empresa simulada"]}
ROWS = [  # código, grupo, rótulo en, rótulo pt, estilo do nome da métrica ("s": "· F1", "p": "· event F1", None: sem métrica)
    ("S1", 0, "relation breaks: alert", "relação quebra: alerta", "s"),
    ("S2", 0, "input changes: log", "entrada muda: log", "s"),
    ("S3", 0, "where: true fields only", "onde: só campos certos", "s"),
    ("S4a", 0, "which way it moved", "para que lado mudou", None),
    ("S4b", 0, "how much, within ⟦tol_dp⟧ sd", "quanto, a menos de ⟦tol_dp⟧ dp", None),
    ("S4c", 0, "became the new normal", "virou o normal novo", None),
    ("S5", 0, "slow drift: log, no alert", "deriva lenta: log, sem alerta", "s"),
    ("S7", 0, "quiet on streams with no change", "quieto em séries sem mudança", None),
    ("L1", 1, "slow real-valued drift", "deriva lenta real", "s"),
    ("L2", 1, "categorical change", "mudança categórica", "s"),
    ("L3", 1, "XOR", "XOR", "s"),
    ("P1L4", 1, "NAB events &lt; ⟦curto⟧ items", "NAB, eventos &lt; ⟦curto⟧ itens", "s"),
    ("P4L4", 1, "SMD events &lt; ⟦curto⟧ items", "SMD, eventos &lt; ⟦curto⟧ itens", "s"),
    ("P5L4", 1, "SMAP events &lt; ⟦curto⟧ items", "SMAP, eventos &lt; ⟦curto⟧ itens", "s"),
    ("P6L4", 1, "MSL events &lt; ⟦curto⟧ items", "MSL, eventos &lt; ⟦curto⟧ itens", "s"),
    ("P1", 2, "NAB", "NAB", "p"),
    ("P1c", 2, "NAB, ⟦aquec⟧-item warm-up · info", "NAB com aquecimento de ⟦aquec⟧", None),
    ("P4", 2, "SMD", "SMD", "p"),
    ("P4o", 2, "SMD where, of ⟦campos_smd⟧ fields", "SMD onde, entre ⟦campos_smd⟧ campos", "s"),
    ("P5", 2, "SMAP", "SMAP", "p"),
    ("P6", 2, "MSL", "MSL", "p"),
    ("M1", 3, "contingency, route, ⟦m1_min⟧ min", "contingência, rota, ⟦m1_min⟧ min", "s"),
    ("M2", 3, "incident, probe, ⟦m2_min⟧ min", "incidente, sonda, ⟦m2_min⟧ min", "s"),
    ("M3", 3, "regime change: new normal, ⟦m3_dias⟧ d", "regime muda: normal novo, ⟦m3_dias⟧ d", None),
    ("M4", 3, "portfolio drift: new normal", "deriva da carteira: normal novo", None),
    ("M5", 3, "back to normal within ⟦m5_h⟧ h", "volta ao normal em até ⟦m5_h⟧ h", None),
]
NOME_METRICA = {"f1": {"en": {"s": "F1", "p": "event F1"}, "pt": {"s": "F1", "p": "F1 por evento"}},
                "sensitivity": {"en": {"s": "recall"}, "pt": {"s": "sensib."}}}


def rotulo(c, en, pt, estilo, lang, ROW):
    """Rótulo da linha com o nome da métrica tirado do rows.json; só P1c (informação) tem métrica e não a mostra."""
    met = ROW[c].get("metric")
    if estilo is None:
        assert met is None or c == "P1c", f"{c}: a linha tem métrica {met} e o rótulo não a mostra"
        return en if lang == "en" else pt
    assert met is not None, f"{c}: o rótulo mostra métrica, mas a linha não tem"
    return f"{en if lang == 'en' else pt} · {NOME_METRICA[met][lang][estilo]}"
SO = {  # linhas só do Sismo: valor mostrado (chave), texto da faixa
    "S4a": ("s4a", 'competitors do not report a direction · the right answer is fixed: ⟦s4a_num⟧ numeric changes go up, ⟦s4a_cat⟧ categorical ones raise category ⟦cat_alvo⟧, so a constant answer also scores ⟦s4a_sempre⟧ · n ⟦s4a_n⟧',
            'os concorrentes não dizem a direção · a resposta certa é fixa: ⟦s4a_num⟧ mudanças numéricas sobem, ⟦s4a_cat⟧ categóricas elevam a categoria ⟦cat_alvo⟧, então uma resposta constante também daria ⟦s4a_sempre⟧ · n ⟦s4a_n⟧'),
    "S4b": ("s4b", "competitors do not report a size · read ⟦itens_tamanho⟧ items after the warning · null ⟦s4b_nulo⟧ · n ⟦s4b_n⟧",
            "os concorrentes não dizem o tamanho · lido ⟦itens_tamanho⟧ itens depois do aviso · nulo ⟦s4b_nulo⟧ · n ⟦s4b_n⟧"),
    "S4c": ("s4c", "competitors do not report a new normal · null ⟦s4c_nulo⟧ · n ⟦s4c_n⟧",
            "os concorrentes não dizem quando virou o normal · nulo ⟦s4c_nulo⟧ · n ⟦s4c_n⟧"),
    "S7": ("⟦s7_alerta⟧ · ⟦s7_log⟧", "Sismo on ⟦s7_n⟧ streams with no change (⟦s7_nul⟧ null, ⟦s7_emb⟧ shuffled; none autocorrelated): alert in ⟦s7_alerta⟧ (ceiling ⟦teto_alerta⟧), log in ⟦s7_log⟧ (⟦teto_log⟧) · they set each †",
           "Sismo em ⟦s7_n⟧ séries sem mudança (⟦s7_nul⟧ nulas, ⟦s7_emb⟧ embaralhadas; nenhuma autocorrelacionada): alerta em ⟦s7_alerta⟧ (teto ⟦teto_alerta⟧), log em ⟦s7_log⟧ (⟦teto_log⟧) · elas dão cada †"),
    "M3": ("m3", "competitors do not report a new normal · null ⟦m3_nulo⟧ · ⟦m3_k⟧ of ⟦m3_n⟧, resting on ⟦m3_reg⟧ distinct records (one record can count for several changes of the same field)",
           "os concorrentes não dizem quando virou o normal · nulo ⟦m3_nulo⟧ · ⟦m3_k⟧ de ⟦m3_n⟧, apoiados em ⟦m3_reg⟧ registros distintos (um registro pode contar para várias mudanças do mesmo campo)"),
    "M4": ("⟦m4_k⟧ ⟦de⟧ ⟦m4_n⟧", "competitors do not report a new normal · fired ⟦m4_vezes⟧ in the life without drift, where it must stay silent",
           "os concorrentes não dizem quando virou o normal · disparou ⟦m4_vezes⟧ na vida sem deriva, onde devia ficar quieto"),
    "P1L4": ("n = ⟦p1l4_n⟧", "no event under ⟦curto⟧ items: NAB events are labeled windows, not durations",
             "nenhum evento com menos de ⟦curto⟧ itens: os eventos do NAB são janelas rotuladas, não durações"),
    "P5L4": ("n = ⟦p5l4_n⟧", "no event under ⟦curto⟧ items in the SMAP approval series", "nenhum evento com menos de ⟦curto⟧ itens nas séries de aprovação do SMAP"),
    "P6L4": ("n = ⟦p6l4_n⟧", "no event under ⟦curto⟧ items in the MSL approval series", "nenhum evento com menos de ⟦curto⟧ itens nas séries de aprovação do MSL"),
    "M5": ("m5", "competitors do not report a return to normal · confirmed ⟦m5_h0⟧ to ⟦m5_h1⟧ h after recovery in ⟦m5_k⟧ of ⟦m5_n⟧, none within ⟦m5_h⟧ h · n ⟦m5_n⟧",
           "os concorrentes não dizem a volta ao normal · confirmou de ⟦m5_h0⟧ a ⟦m5_h1⟧ h depois da volta em ⟦m5_k⟧ de ⟦m5_n⟧, nenhuma em até ⟦m5_h⟧ h · n ⟦m5_n⟧"),
}
EST = {
    "en": {"pass": "passes", "fail": "does not pass", "null": "does not pass · null over ceiling", "info": "info only", "lc": "limit confirmed", "ln": "limit not confirmed", "nm": "limit not measured"},
    "pt": {"pass": "passa", "fail": "não passa", "null": "não passa · nulo acima do teto", "info": "só informação", "lc": "limite confirmado", "ln": "limite não confirmado", "nm": "limite não medido"},
}
TXT_TABELA = {
    "en": dict(top="public benchmark · approval run", h="Every row, every method",
        sub="All ⟦linhas⟧ rows of the benchmark against Sismo and the ⟦concorrentes⟧ competitors, passes and failures, each with its number.",
        row="row", st="verdict",
        leg="Higher is better in every row. Metric: F1 per event, or recall (share of events found) where the row says so. Each method has two configurations, default and tuned on a separate set; the cell shows its best one under the false-alarm ceiling. <span style=\"color:#e3c47a\">Brass box</span>: winner of the row, the highest value among the methods allowed in it (none when that value is ⟦zero⟧). † every configuration that scores in the row is over the ceiling on streams with no change (alert ⟦teto_alerta⟧, log ⟦teto_log⟧, as each row requires; on public data, ⟦teto_pub⟧ warnings per ⟦mil⟧ items; company ⟦teto_emp⟧): the cell shows its best value, and it cannot win the row, Sismo included. On the limit rows the protocol does not apply Sismo’s own null, so it has no † there. S3: the per-field competitors can only score on the ⟦ent_n⟧ input changes (ADWIN ⟦ent_adwin⟧ of ⟦ent_n⟧); the ⟦rel_n⟧ relation breaks count only with an alert. SMD under ⟦curto⟧ items: Sismo finds ⟦p4l4_k⟧ of ⟦p4l4_n⟧ (recall ⟦p4l4⟧; with ⟦p4l4_falsos⟧ false warnings its F1 there is ⟦p4l4_f1⟧), and the only allowed competitor is CJSD ‡, so that verdict is marked ‡. – did not run: the method needs a labeled response or does not fit the data. ‡ adapter defect in this archived run (independent review, ⟦data⟧): CJSD could not warn without a response (public data, company), so those values are not a measurement; the weighted WATCH adapter used future data. A corrected comparison will run under a new protocol. CJSD is Oda’s method; WATCH, that of Prinster et al.",
        foot="Protocol verdict: <span style=\"font-style: italic\">not approved</span>. ⟦passam⟧ of the ⟦decidem⟧ rows that decide passed: ⟦vit⟧ wins, ⟦cap⟧ by capacity (S3, where competitors cannot score the relation breaks), ⟦emp⟧ ties, ⟦nul⟧ against a null or a ceiling; each is compared with the best allowed competitor at two standard errors.",
        why="On the public data its null rises, possibly from unlabeled changes in the training stretch or from autocorrelation (hypotheses not yet checked). It passes every synthetic row that decides (S3 by capacity); its own misses stay in the table: contingency, portfolio drift, return to normal.",
        sig="Approval protocol frozen before the approval run (sha256 ⟦hash⟧, which proves content, not date) · ⟦series⟧ series, rerun with the publication code: identical · one command reproduces the rows; these boards derive from them · github.com/LimiarResearch/sismo"),
    "pt": dict(top="bancada pública · rodada de aprovação", h="Todas as linhas, todos os métodos",
        sub="As ⟦linhas⟧ linhas da bancada contra o Sismo e os ⟦concorrentes⟧ concorrentes, as que passam e as que não passam, cada uma com o seu número.",
        row="linha", st="veredito",
        leg="Maior é melhor em todas as linhas. Métrica: F1 por evento, ou sensibilidade (fração dos eventos achados) onde a linha diz sensib. Cada método tem duas configurações, a padrão e a ajustada num conjunto separado; a célula mostra a melhor abaixo do teto de alarme falso. <span style=\"color:#e3c47a\">Caixa de latão</span>: vencedor da linha, o maior valor entre os métodos permitidos nela (nenhum quando esse valor é ⟦zero⟧). † toda configuração que pontua na linha passa do teto em séries sem mudança (alerta ⟦teto_alerta⟧, log ⟦teto_log⟧, conforme cada linha exige; nas bases públicas, ⟦teto_pub⟧ aviso por ⟦mil⟧ itens; empresa ⟦teto_emp⟧): a célula mostra o melhor valor, e ele não pode ganhar a linha, o Sismo inclusive. Nas linhas de limite o protocolo não aplica o nulo do próprio Sismo, por isso ali ele não leva †. S3: os concorrentes por campo só pontuam nas ⟦ent_n⟧ mudanças de entrada (ADWIN ⟦ent_adwin⟧ de ⟦ent_n⟧); as ⟦rel_n⟧ quebras de relação só contam com alerta. SMD abaixo de ⟦curto⟧ itens: o Sismo acha ⟦p4l4_k⟧ de ⟦p4l4_n⟧ (sensibilidade ⟦p4l4⟧; com ⟦p4l4_falsos⟧ avisos falsos o F1 dele ali é ⟦p4l4_f1⟧), e o único concorrente permitido é o CJSD ‡, por isso esse veredito leva ‡. – não rodou: o método precisa de resposta rotulada ou não cabe nos dados. ‡ defeito de adaptador nesta rodada arquivada (revisão independente, ⟦data⟧): o CJSD não conseguia avisar sem resposta (bases públicas, empresa), então esses valores não são medida; o adaptador ponderado do WATCH usava dados futuros. Uma comparação corrigida vai rodar sob um protocolo novo. O CJSD é o método de Oda; o WATCH, o de Prinster et al.",
        foot="Veredito do protocolo: <span style=\"font-style: italic\">não aprovado</span>. ⟦passam⟧ das ⟦decidem⟧ linhas que decidem passaram: ⟦vit⟧ vitórias, ⟦cap⟧ por capacidade (S3, onde os concorrentes não pontuam nas quebras de relação), ⟦emp⟧ empates, ⟦nul⟧ contra nulo ou teto; cada uma contra o melhor concorrente permitido, a dois erros-padrão.",
        why="Nas bases públicas o nulo dele sobe, talvez por mudanças sem rótulo no treino ou por autocorrelação (hipóteses não verificadas). Passa em todas as sintéticas que decidem (S3 por capacidade); as falhas ficam na tabela: contingência, deriva da carteira, volta ao normal.",
        sig="Protocolo de aprovação congelado antes da rodada de aprovação (sha256 ⟦hash⟧, que prova o conteúdo, não a data) · ⟦series⟧ séries, rodadas de novo com o código de publicação: idênticas · um comando reproduz as linhas; estas telas derivam delas · github.com/LimiarResearch/sismo"),
}
COLS = "grid-template-columns: 300px 96px repeat(15, minmax(0, 1fr)) 214px"
CELL = "display: flex; align-items: center; justify-content: flex-end; padding-right: 10px; font-variant-numeric: lining-nums tabular-nums"


def estado(x):
    st = x["status"]
    if st == "PASSED": return "pass"
    if st == "FAILED (detector's null above the ceiling)": return "null"
    if st == "FAILED": return "fail"
    if st == "information only": return "info"
    if re.fullmatch(r"limit L\d not measured \(n = 0\)", st): return "nm"
    if re.fullmatch(r"limit L\d not confirmed in this sample", st): return "ln"
    if re.fullmatch(r"limit L\d confirmed", st): return "lc"
    raise SystemExit(f"status desconhecido em rows.json: {st}")


def tabela(lang, VL, ROW, N):
    TAB = N["tabela"]
    t = {k: preenche(v, VL) for k, v in TXT_TABELA[lang].items()}
    num = lambda v: m(f"{v:.3f}".replace(".", "," if lang == "pt" else "."))
    h = [f'''<div style="display: grid; {COLS}; align-items: end; height: 46px; border-bottom: 1px solid #dce6ff33; font-style: italic; font-size: 14px; line-height: 1.15; color: #9c988e">
      <span style="padding-bottom: 8px">{t["row"]}</span>
      <span style="padding: 0 10px 8px 0; text-align: right; color: #dce6ff; font-weight: 600; font-style: normal; font-size: 17px">Sismo</span>''']
    for n in HEAD[lang]:
        h.append(f'      <span style="padding: 0 10px 8px 0; text-align: right">{n}</span>')
    h.append(f'      <span style="padding: 0 0 8px 14px">{t["st"]}</span>\n    </div>')
    g = -1
    SC = "box-shadow: inset 1px 0 0 rgba(220, 230, 255, 0.35), inset -1px 0 0 rgba(220, 230, 255, 0.35)"
    DAG = '<span style="width: 0; overflow: visible; font-size: 11px; margin-left: 1px">†</span>'
    DDAG = '<span style="width: 0; overflow: visible; font-size: 11px; margin-left: 1px; color: #d8552b">‡</span>'

    def pinta(val, lo, hi, venc):
        if venc:
            return "background: rgba(200, 162, 75, 0.20); color: #e3c47a; font-weight: 600; box-shadow: inset 0 0 0 1px rgba(200, 162, 75, 0.55)"
        q = (0.0 if hi <= 0 else 1.0) if hi <= lo else (val - lo) / (hi - lo)
        ink = tuple(round(a + (b - a) * q) for a, b in ((0x80, 0xf1), (0x7e, 0xed), (0x78, 0xe4)))
        return f"background: rgba(220, 230, 255, {0.02 + 0.19 * q:.3f}); color: rgb{ink}"
    for c, gi, en, pt, estilo in ROWS:
        if gi != g:
            g = gi
            h.append(f'    <div style="height: 31px; display: flex; align-items: flex-end; padding-bottom: 5px; box-sizing: border-box; font-style: italic; font-size: 15px; color: #9c988e; border-bottom: 1px solid #23262f">{G[lang][gi]}</div>')
        x = ROW[c]; lab = preenche(rotulo(c, en, pt, estilo, lang, ROW), VL)
        es = estado(x)
        dim = gi == 1 or es == "info"
        cells = []
        if c in SO:
            k, ten, tpt = SO[c]
            v = preenche(k.replace("⟦de⟧", "of" if lang == "en" else "de"), VL) if "⟦" in k else m(VL[k])
            cells.append(f'<span style="grid-column: span 15; display: flex; align-items: center; padding: 0 10px; font-style: italic; font-size: 14px; color: #9c988e; white-space: nowrap; overflow: hidden">{preenche(ten if lang == "en" else tpt, VL)}</span>')
            st = pinta(1, 0, 1, True) if es == "pass" else "color: #9c988e"
            sis = f'<span style="{CELL}; {st}; {SC}">{v}</span>'
        else:
            row = TAB[c]
            vals = {k: (row[k][0], row[k][1], row[k][2]) for k in COMP if row.get(k)}
            vals["_sismo"] = (row["detector"][0], row["detector"][1], False)
            ok = [v for v, e, _ in vals.values() if e]
            hi = max(ok) if ok else 0; lo = min(ok) if ok else 0

            def cel(k, extra=""):
                xx = vals.get(k)
                if not xx:
                    return f'<span style="{CELL}; color: #4a4c55; {extra}">–</span>'
                val, e, bad = xx
                if not e:
                    s = f'<span style="{CELL}; color: #5e5c57; {extra}">{num(val)}{DAG}</span>'
                else:
                    venc = hi > 0 and abs(val - hi) < 1e-9
                    st = pinta(val, lo, hi, venc)
                    if venc and extra:
                        extra = ""
                    s = f'<span style="{CELL}; {st}; {extra}">{num(val)}</span>'
                return s.replace("</span>", DDAG + "</span>", 1) if bad else s
            sis = cel("_sismo", SC)
            for k in COMP:
                cells.append(cel(k))
        dot = {"pass": '<span style="width: 7px; height: 7px; border-radius: 50%; background: #c8a24b; flex-shrink: 0"></span>',
               "fail": '<span style="width: 5px; height: 5px; border-radius: 50%; border: 1px solid #f1ede4; flex-shrink: 0"></span>',
               "null": '<span style="width: 5px; height: 5px; border-radius: 50%; border: 1px solid #f1ede4; flex-shrink: 0"></span>'}.get(es, '<span style="width: 7px; flex-shrink: 0"></span>')
        stc = {"pass": "#c8a24b", "fail": "#f1ede4", "null": "#f1ede4"}.get(es, "#9c988e")
        stz = "13px" if es == "null" else "14px"
        empate = (" · tied" if lang == "en" else " · empate") if x.get("verdict") == "TIED" and es == "pass" else ""
        perm = [k for k in COMP if TAB.get(c, {}).get(k) and TAB[c][k][1]]
        ddag_v = DDAG if (c in TAB and x.get("limit") and perm and all(TAB[c][k][2] for k in perm)) else ""
        h.append(f'''    <div style="display: grid; {COLS}; height: 27px; border-bottom: 1px solid #23262f; font-size: 16px{"; opacity: 0.8" if dim else ""}">
      <span style="display: flex; align-items: center; gap: 10px; white-space: nowrap; overflow: hidden"><span style="width: 40px; flex-shrink: 0; font-size: 13px; color: #9c988e">{c}</span><span style="font-size: 15px">{lab}</span></span>
      {sis}
      {"".join(cells)}
      <span style="display: flex; align-items: center; gap: 7px; padding-left: 14px; font-style: italic; font-size: {stz}; color: {stc}; white-space: nowrap">{dot}{EST[lang][es]}{empate}{ddag_v}</span>
    </div>''')
    body = "\n".join(h)
    return f'''<!doctype html>
<html lang="{'en' if lang == 'en' else 'pt-BR'}">
<head>
<meta charset="utf-8">
<title>Sismo: {'full results' if lang == 'en' else 'resultados completos'}</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,300..600;1,6..72,300..600&amp;family=Poiret+One&amp;display=swap">
<style>
body{{margin:0}}
a{{color:#dce6ff}}a:hover{{color:#f1ede4}}
</style>
</helmet>
<div style="width: 1920px; height: 1350px; box-sizing: border-box; padding: 44px 64px 40px; background: #06070b; color: #f1ede4; font-family: Newsreader, Georgia, serif; display: flex; flex-direction: column">
  <div style="display: flex; justify-content: space-between; align-items: center; height: 44px">
    <img src="{LOGO}" alt="Limiar Research" style="height: 44px; width: auto">
    <span style="font-style: italic; font-size: 18px; color: #9c988e">{t["top"]}</span>
  </div>
  <div style="margin-top: 24px; display: flex; align-items: baseline; gap: 32px">
    <h1 style="margin: 0; font-family: 'Poiret One', Futura, sans-serif; font-weight: 400; font-size: 54px; line-height: 1.05; letter-spacing: 0.01em; white-space: nowrap">{t["h"]}</h1>
    <p style="margin: 0; font-style: italic; font-weight: 300; font-size: 21px; line-height: 1.35; color: #9c988e">{t["sub"]}</p>
  </div>
  <div style="margin-top: 26px; display: flex; flex-direction: column">
{body}
  </div>
  <div style="margin-top: auto; display: flex; flex-direction: column; gap: 8px">
    <p style="margin: 0; font-size: 14px; line-height: 1.45; color: #9c988e">{t["leg"]}</p>
    <p style="margin: 0; font-size: 20px; line-height: 1.35">{t["foot"]}</p>
    <p style="margin: 0; padding-left: 14px; border-left: 1px solid #dce6ff; font-size: 16px; line-height: 1.45; color: #f1ede4">{t["why"]}</p>
    <p style="margin: 0; font-style: italic; font-size: 14px; color: #9c988e">{t["sig"]}</p>
  </div>
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{{"$preview":{{"width":1920,"height":1350}}}}'>
class Component extends DCLogic {{
  renderVals() {{ return {{}}; }}
}}
</script>
</body>
</html>
'''


# ------------------------------------------------------------------ tela de recursos
NOMES = [("detector", "Sismo", "Sismo"), ("page_hinkley", "Page-Hinkley", "Page-Hinkley"), ("cusum", "CUSUM", "CUSUM"), ("ewma", "EWMA", "EWMA"),
         ("adwin", "ADWIN", "ADWIN"), ("kswin", "KSWIN", "KSWIN"), ("ddm", "DDM", "DDM"), ("hddm_a", "HDDM_A", "HDDM_A"), ("hddm_w", "HDDM_W", "HDDM_W"),
         ("per_field_test", "Per-field test", "Teste por campo"), ("cjsd", "CJSD", "CJSD"), ("watch", "WATCH", "WATCH"), ("ctm", "CTM", "CTM"),
         ("isolation_forest", "Isolation forest", "Isolation forest"), ("matrix_profile", "Matrix profile", "Matrix profile"), ("htm", "HTM", "HTM")]
TXT_RECURSOS = {
    "en": dict(lang="en", title="Sismo: capabilities", tag="public benchmark · approval run", h1="All of it in one warning",
        sub="What each method returns in this runner, not who does it best. None of the pieces is new.",
        cols=["method", "where: right field", "when it started", "which way, how much", "new normal", "alert F1", "log F1", "no labels: incidents"],
        leg=["where: changes in which every field named is a true one, among up to ⟦campos_max⟧; the per-field methods can only score on the ⟦ent_n⟧ input changes of ⟦s3_total⟧ (ADWIN ⟦ent_adwin⟧ of ⟦ent_n⟧), since the relation breaks count only with an alert · when: among the changes it detected in S1 and S2, start within ⟦tol_quando⟧ items (Sismo ⟦quando_k⟧ of ⟦quando_n⟧; CUSUM ⟦cusum_k⟧ of ⟦cusum_n⟧, with the configurations of the full table, the S1 one over the ceiling; over all ⟦q_total⟧ changes, ⟦q480_det⟧ and ⟦q480_cusum⟧); among the competitors only CUSUM and matrix profile estimate a start · which way, how much: direction right (the right answer is fixed in this test: numeric changes go up, categorical ones raise one category) and size within ⟦tol_dp⟧ sd, read ⟦itens_tamanho⟧ items after the warning · new normal: synthetic steps that stay, reported as the new normal (return to normal fails, see the full results) · alert and log: event F1 · no labels: incidents found in the simulated company, which has no labels (⟦m2_n⟧)",
             "† every configuration of it that scores is over the false-alarm ceiling on streams with no change; otherwise the cell shows its best one under it; in “when”, † if a configuration used is over it · – does not return it here (matrix profile estimates a start but found no change in S1 or S2; a two-sided CUSUM can give direction and size, not computed here) · CJSD (Oda) and WATCH (Prinster et al.): the closest published relatives of the alert and log split · · not run there (cost) · ‡ adapter defect in this archived run, found by an independent review on ⟦data⟧: CJSD could not warn without a response; its incident value is not a measurement; the weighted WATCH adapter scaled with future data on the rows with a response."],
        foot="Approval protocol frozen before the approval run (sha256 ⟦hash⟧, which proves content, not date) · ⟦concorrentes⟧ competitors from river, scikit-learn, stumpy, the NAB community and their authors' code · one command reproduces the rows; these boards derive from them."),
    "pt": dict(lang="pt-BR", title="Sismo: recursos", tag="bancada pública · rodada de aprovação", h1="Tudo num aviso só",
        sub="O que cada método devolve nesta bancada, não quem faz melhor. Nenhuma das peças é nova.",
        cols=["método", "onde: campo certo", "quando começou", "para que lado, quanto", "normal novo", "F1 de alerta", "F1 de log", "sem rótulo: incidentes"],
        leg=["onde: mudanças em que todo campo citado é um dos verdadeiros, entre até ⟦campos_max⟧; os métodos por campo só pontuam nas ⟦ent_n⟧ mudanças de entrada das ⟦s3_total⟧ (ADWIN ⟦ent_adwin⟧ de ⟦ent_n⟧), porque as quebras de relação só contam com alerta · quando: entre as mudanças que ele achou em S1 e S2, começo a menos de ⟦tol_quando⟧ itens (Sismo ⟦quando_k⟧ de ⟦quando_n⟧; CUSUM ⟦cusum_k⟧ de ⟦cusum_n⟧, com as configurações da tabela completa, a de S1 acima do teto; sobre todas as ⟦q_total⟧ mudanças, ⟦q480_det⟧ e ⟦q480_cusum⟧); entre os concorrentes, só o CUSUM e o matrix profile estimam o começo · para que lado, quanto: direção certa (a resposta certa é fixa neste teste: as mudanças numéricas sobem, as categóricas elevam uma categoria) e tamanho a menos de ⟦tol_dp⟧ dp, lido ⟦itens_tamanho⟧ itens depois do aviso · normal novo: degraus sintéticos que ficam, ditos como normal novo (a volta ao normal reprova, ver os resultados completos) · alerta e log: F1 por evento · sem rótulo: incidentes achados na empresa simulada, que não tem rótulo (⟦m2_n⟧)",
             "† toda configuração dele que pontua passa do teto de alarmes falsos nas séries sem mudança; senão a célula mostra a melhor abaixo dele; em “quando”, † se uma configuração usada passa dele · – não devolve aqui (o matrix profile estima o começo, mas não achou mudança em S1 nem S2; um CUSUM bilateral pode dar direção e tamanho, não calculados aqui) · CJSD (Oda) e WATCH (Prinster et al.): os parentes publicados mais próximos da separação entre alerta e log · · não rodou ali (custo) · ‡ defeito de adaptador nesta rodada arquivada, achado por uma revisão independente em ⟦data⟧: o CJSD não conseguia avisar sem resposta; o valor dele nos incidentes não é medida; o adaptador ponderado do WATCH escalava com dados futuros nas linhas com resposta."],
        foot="Protocolo de aprovação congelado antes da rodada de aprovação (sha256 ⟦hash⟧, que prova o conteúdo, não a data) · ⟦concorrentes⟧ concorrentes do river, do scikit-learn, do stumpy, da comunidade do NAB e do código dos autores · um comando reproduz as linhas; estas telas derivam delas."),
}


def recursos(lang, VL, N):
    t = TXT_RECURSOS[lang]; C = N["recursos"]
    dec = (lambda s: s.replace(".", ",")) if lang == "pt" else (lambda s: s)

    def cel(x, eu, pct, chave=None):
        if x == "N" or x == "NR" or x is None:
            return ("–" if x != "NR" else "·"), "#5a574f", 22, "none", "Newsreader, Georgia, serif"
        if chave:
            s = m(VL[chave]); ok, bad = True, False
        else:
            v, ok, bad = x
            s = m(("100%" if round(100 * v, 1) == 100 else dec(f"{100 * v:.1f}%")) if pct else dec(f"{v:.3f}"))
        s += ("" if ok else " †") + (" ‡" if bad else "")
        return s, "#dce6ff" if eu else ("#f1ede4" if ok else "#6f6b63"), 19, "0 0 18px rgba(220, 230, 255, 0.45)" if eu else "none", "'Poiret One', Futura, sans-serif"
    linhas = []
    for k, en, pt in NOMES:
        eu = k == "detector"
        if k == "htm":
            cs = [cel("NR", 0, 1), cel("N", 0, 1), cel("N", 0, 1), cel("N", 0, 1), cel("N", 0, 1), cel("NR", 0, 1), cel("NR", 0, 1)]
        else:
            c = C[k]; q = c["quando"]
            cs = [cel(c["onde"], eu, True), cel(None if q is None else [q[0] / q[1], q[2], False], eu, True),
                  cel([1, True, False], eu, True, "dir_pc") if eu else cel(None, eu, True),
                  cel([1, True, False], eu, True, "nn_pc") if eu else cel(None, eu, True),
                  cel(c["alerta"], eu, False), cel(c["log"], eu, False), cel(c["incidentes"], eu, True)]
        bg = "rgba(220, 230, 255, 0.06)" if eu else "transparent"
        nome = en if lang == "en" else pt
        spans = "\n".join(f'        <span style="text-align: center; font-family: {f}; font-size: {z}px; color: {cor}; text-shadow: {gl}">{s}</span>' for s, cor, z, gl, f in cs)
        linhas.append(f'''      <div style="display: grid; grid-template-columns: 200px repeat(7, minmax(0, 1fr)); column-gap: 6px; align-items: center; height: 43px; border-bottom: 1px solid #23262f; background: {bg}">
        <span style="font-size: 20px; color: {'#dce6ff' if eu else '#f1ede4'}; font-weight: {600 if eu else 400}; padding-left: {10 if eu else 0}px">{nome}</span>
{spans}
      </div>''')
    head = "\n".join(f'    <span style="text-align: center">{c}</span>' for c in t["cols"][1:])
    leg = "\n".join(f"    <span>{preenche(x, VL)}</span>" for x in t["leg"])
    grid = "200px repeat(7, minmax(0, 1fr))"
    return f'''<!doctype html>
<html lang="{t["lang"]}">
<head>
<meta charset="utf-8">
<title>{t["title"]}</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,300..600;1,6..72,300..600&amp;family=Poiret+One&amp;display=swap">
<style>
body{{margin:0}}
a{{color:#dce6ff}}a:hover{{color:#f1ede4}}
</style>
</helmet>
<div style="width: 1080px; height: 1350px; box-sizing: border-box; padding: 64px 72px 56px; background: #06070b; color: #f1ede4; font-family: Newsreader, Georgia, serif; display: flex; flex-direction: column">
  <div style="display: flex; justify-content: space-between; align-items: center; height: 44px">
    <img src="{LOGO}" alt="Limiar Research" style="height: 44px; width: auto">
    <span style="font-style: italic; font-size: 18px; color: #9c988e">{t["tag"]}</span>
  </div>
  <h1 style="margin: 40px 0 0; font-family: 'Poiret One', Futura, sans-serif; font-weight: 400; font-size: 58px; line-height: 1.06; letter-spacing: 0.01em">{t["h1"]}</h1>
  <p style="margin: 14px 0 0; font-style: italic; font-weight: 300; font-size: 23px; line-height: 1.35; color: #9c988e">{t["sub"]}</p>
  <div style="margin-top: 30px; display: grid; grid-template-columns: {grid}; column-gap: 6px; align-items: end; padding-bottom: 12px; border-bottom: 1px solid #23262f; font-style: italic; font-size: 15px; line-height: 1.25; color: #9c988e">
    <span>{t["cols"][0]}</span>
{head}
  </div>
  <div style="display: flex; flex-direction: column">
{chr(10).join(linhas)}
  </div>
  <div style="margin-top: 14px; display: flex; flex-direction: column; gap: 4px; font-size: 14px; line-height: 1.4; color: #9c988e">
{leg}
  </div>
  <p style="margin: auto 0 0; font-style: italic; font-size: 15px; color: #9c988e">{preenche(t["foot"], VL)}</p>
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{{"$preview":{{"width":1080,"height":1350}}}}'>
class Component extends DCLogic {{
  renderVals() {{ return {{}}; }}
}}
</script>
</body>
</html>
'''


# ------------------------------------------------------------------ geração e conferência
ARQUIVOS = [("Capabilities-en", "en"), ("Purpose-en", "en"), ("Scorecard-en", "en"), ("Results-en", "en"),
            ("Recursos-pt", "pt"), ("Proposito-pt", "pt"), ("Placar-pt", "pt"), ("Resultados-pt", "pt")]


def gera(repo, N):
    VV, ROW = valores(repo, N)
    out = {}
    for nome, lang in ARQUIVOS:
        VL = VV[lang]
        if nome in ("Results-en", "Resultados-pt"):
            out[nome] = tabela(lang, VL, ROW, N)
        elif nome in ("Capabilities-en", "Recursos-pt"):
            out[nome] = recursos(lang, VL, N)
        else:
            out[nome] = de_molde(nome, VL)
    return out


def texto_visivel(h):
    h = re.sub(r"<script.*?</script>|<style.*?</style>|<head>.*?</head>", " ", h, flags=re.S)
    return _html.unescape(re.sub(r"<[^>]+>", " ", h))


def digitos_sem_fonte(h):
    """Dígitos visíveis que não vieram de um valor calculado nem são identificadores."""
    t = re.sub(r"\x01[^\x02]*\x02", " ", texto_visivel(h))
    return [tok for tok in re.findall(r"[A-Za-z0-9_]*\d[A-Za-z0-9_]*", t) if not IDENT.match(tok)]


def gera_conferido(repo, N):
    MARCA[0] = True
    marcadas = gera(repo, N)
    MARCA[0] = False
    soltos = {n: digitos_sem_fonte(h) for n, h in marcadas.items()}
    soltos = {n: s for n, s in soltos.items() if s}
    if soltos:
        raise SystemExit(f"dígitos sem fonte no texto das telas: {soltos}")
    final = gera(repo, N)
    assert all(final[n] == marcadas[n].replace("\x01", "").replace("\x02", "") for n in final)
    return final


if __name__ == "__main__":
    repo, num, saida = sys.argv[1:4]
    N = json.load(abre(num))
    telas = gera_conferido(repo, N)
    os.makedirs(saida, exist_ok=True)
    for nome, h in telas.items():
        open(os.path.join(saida, nome + ".dc.html"), "w", encoding="utf-8", newline="\n").write(h)
    print("ok: 8 telas geradas; nenhum dígito visível sem fonte")
