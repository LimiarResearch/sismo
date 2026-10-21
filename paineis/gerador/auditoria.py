"""Auditoria das telas: confere o HTML publicado das telas contra o que os dados produzem.

Uso: python auditoria.py <repositório> <numeros.json> <pasta com o HTML das telas> [<pasta publication> <pasta lives>]

0. Regeneração: roda numeros_das_telas.py de novo a partir do rows.json (e das saídas da rodada, quando as pastas são
   dadas) e exige o mesmo numeros.json; depois roda telas.py, que gera as oito telas a partir desses números e para se houver
   dígito visível sem fonte, e exige que cada tela publicada seja igual, byte a byte, à gerada. Qualquer caractere mudado em
   qualquer tela (número, rótulo, cabeçalho, hash, nome de método) é um problema.
1 a 4. Conferências independentes do gerador, para pegar um erro de regra no próprio gerador: cada célula, †, ‡, caixa de
   vencedor e veredito das tabelas contra rows.json; cada célula de recursos; frases com números escritas de novo aqui a
   partir do cálculo, nos dois idiomas, tela por tela; paridade dos números entre inglês e português.

O que não confere: se cada PNG em prints/ é o render deste HTML (os PNG são capturas dele com Chromium); sem as pastas
publication e lives, os números do universo vêm do numeros.json dado, sem recálculo (a auditoria avisa).
"""
import json, os, re, sys, collections

import subprocess, tempfile, difflib
sys.stdout.reconfigure(encoding="utf-8")
REPO, NUM, D = sys.argv[1], sys.argv[2], sys.argv[3]
PARCIAL = len(sys.argv) > 4 and sys.argv[4] == "--parcial"
PUB, VIDAS = (sys.argv[4], sys.argv[5]) if len(sys.argv) > 5 else (None, None)
AQUI = os.path.dirname(os.path.abspath(__file__))
abre = lambda p: open(p, encoding="utf-8")
R = json.load(abre(os.path.join(REPO, "results", "publication", "rows.json"))); N = json.load(abre(NUM))
ROW = {}
for x in R:
    c = x["row"].split()[0]
    ROW["L" + x["row"].split()[3][1] if c == "S6" else c] = x
TAB, F, U = N["tabela"], N["fatos"], N["universo"]
FAM = ["page_hinkley", "cusum", "ewma", "adwin", "kswin", "ddm", "hddm_a", "hddm_w", "per_field_test", "cjsd", "watch", "ctm",
       "isolation_forest", "matrix_profile", "htm"]
erros = []; conferidos = collections.Counter()
if not PUB and not PARCIAL:
    erros.append("faltam as pastas publication e lives: sem elas o universo (séries, S7, S3 por tipo, M3, S4a, M2) não é recalculado; "
                 "para uma auditoria parcial, de propósito, passe --parcial no lugar delas")

# 0. regeneração
with tempfile.TemporaryDirectory() as tmp:
    novo = os.path.join(tmp, "numeros.json")
    cmd = [sys.executable, "-X", "utf8", "-I", os.path.join(AQUI, "numeros_das_telas.py"), REPO, novo] + ([PUB, VIDAS] if PUB else [])
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        erros.append(f"numeros_das_telas.py falhou: {r.stderr.strip()[-300:]}")
    else:
        N2 = json.load(abre(novo))
        if not PUB:
            N2["universo"] = N["universo"]
            for k in ("S3_capacidade",):
                if k in N["fatos"]: N2["fatos"][k] = N["fatos"][k]
            print("AUDITORIA PARCIAL: o universo (séries, S7, S3 por tipo, M3, S4a, M2) vem do numeros.json dado, sem recálculo")
        conferidos["numeros.json recalculado"] += 1
        if N2 != N:
            dif = [k for k in set(N) | set(N2) if N.get(k) != N2.get(k)]
            erros.append(f"numeros.json dado difere do recalculado em: {sorted(dif)}")
sys.path.insert(0, AQUI)
import telas as _telas
try:
    geradas = _telas.gera_conferido(REPO, N)
except SystemExit as e:
    geradas = {}; erros.append(f"telas.py: {e}")
for nome, h in geradas.items():
    esperado = h.replace(_telas.LOGO, "marca.png")
    p = os.path.join(D, nome + ".html")
    conferidos["telas regeneradas"] += 1
    if not os.path.exists(p):
        erros.append(f"{nome}: arquivo ausente"); continue
    publicado = abre(p).read()
    if publicado != esperado:
        a_, b_ = _telas.texto_visivel(publicado).split(), _telas.texto_visivel(esperado).split()
        dif = [d for d in difflib.unified_diff(b_, a_, lineterm="", n=3) if d[:1] in "+-" and d[:3] not in ("+++", "---")]
        erros.append(f"{nome}: difere do gerado ({' '.join(dif[:6])[:160] or 'diferença fora do texto visível'})")
txt = lambda h: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h).replace("&lt;", "<").replace("&amp;", "&")).strip()
TELAS = {"C": ("Capabilities-en", "Recursos-pt"), "P": ("Purpose-en", "Proposito-pt"), "S": ("Scorecard-en", "Placar-pt"),
         "R": ("Results-en", "Resultados-pt")}
HTML = {n: abre(f"{D}/{n}.html").read() for par in TELAS.values() for n in par}
TEXTO = {n: re.sub(r" ([.,;:)])", r"\1", txt(h[h.index("<body"):])) for n, h in HTML.items()}


def num(s, lang):
    s = s.replace("†", "").replace("‡", "").strip()
    if lang == "pt":
        s = s.replace(".", "").replace(",", ".")
    return float(s)


def esperado_veredito(c, lang):
    st = ROW[c]["status"]; v = ROW[c].get("verdict")
    conhecidos = r"PASSED|FAILED|FAILED \(detector's null above the ceiling\)|information only|limit L\d (confirmed|not confirmed in this sample|not measured \(n = 0\))"
    if not re.fullmatch(conhecidos, st):
        return f"<status desconhecido: {st}>"
    en = ("passes" if st == "PASSED" else "does not pass · null over ceiling" if "null above" in st else "does not pass" if st == "FAILED"
          else "info only" if st == "information only" else "limit confirmed" if "confirmed" in st and "not" not in st
          else "limit not confirmed" if "not confirmed" in st else "limit not measured")
    if v == "TIED" and st == "PASSED":
        en += " · tied"
    pt = {"passes": "passa", "does not pass": "não passa", "does not pass · null over ceiling": "não passa · nulo acima do teto",
          "info only": "só informação", "limit confirmed": "limite confirmado", "limit not confirmed": "limite não confirmado",
          "limit not measured": "limite não medido", "passes · tied": "passa · empate"}[en]
    return en if lang == "en" else pt


def _independentes():
    # 1. tabela completa
    for lang, f in (("en", "Results-en"), ("pt", "Resultados-pt")):
        h = HTML[f]
        partes = re.split(r'<span style="width: 40px; flex-shrink: 0; font-size: 13px; color: #9c988e">([A-Z0-9a-z]+)</span>', h)
        vistos = set()
        for i in range(1, len(partes), 2):
            c, seg = partes[i], partes[i + 1].split("</div>")[0]
            vistos.add(c)
            cel = re.findall(r'(<span style="display: flex; align-items: center; justify-content: flex-end; padding-right: 10px; font-variant-numeric[^"]*"[^>]*>.*?</span>)(?=<span style="display: flex|\s*<span style="display: flex|\s*<span style="grid-column|\s*<span style="display: flex; align-items: center; gap: 7px)', seg, re.S)
            vtxt = txt(re.findall(r'gap: 7px; padding-left: 14px[^>]*>(.*?)</span>\s*$', seg.strip(), re.S)[0])
            verd = vtxt.replace("‡", "").strip()
            conferidos["vereditos"] += 1
            if verd != esperado_veredito(c, lang):
                erros.append(f"{lang} {c}: veredito '{verd}' esperado '{esperado_veredito(c, lang)}'")
            # ‡ no veredito: linha de limite cujo único concorrente permitido tem defeito de adaptador
            if c in TAB:
                perm = [k for k in FAM if TAB[c].get(k) and TAB[c][k][1]]
                deve = ROW[c].get("limit") is not None and bool(perm) and all(TAB[c][k][2] for k in perm)
            else:
                deve = False
            if bool(deve) != ("‡" in vtxt):
                erros.append(f"{lang} {c}: ‡ no veredito {'faltando' if deve else 'sobrando'}")
            if c not in TAB:
                if c in ("S4a", "S4b", "S4c", "M3", "M5"):
                    v = txt(cel[0]) if cel else None
                    conferidos["células"] += 1
                    if v is None or abs(num(v, lang) - ROW[c]["detector"]) > 0.00051:
                        erros.append(f"{lang} {c}: Sismo {v} esperado {ROW[c]['detector']:.3f}")
                continue
            if len(cel) != 16:
                erros.append(f"{lang} {c}: {len(cel)} células"); continue
            vals = {}
            for nome, html in zip(["detector"] + FAM, cel):
                t = txt(html); e = TAB[c][nome]
                conferidos["células"] += 1
                if e is None:
                    if t != "–": erros.append(f"{lang} {c} {nome}: '{t}' esperado '–'")
                    continue
                if t in ("–", "n = 0"):
                    erros.append(f"{lang} {c} {nome}: '{t}' esperado {e[0]:.3f}"); continue
                if abs(num(t, lang) - e[0]) > 0.00051: erros.append(f"{lang} {c} {nome}: {t} esperado {e[0]:.3f}")
                if ("†" in t) == bool(e[1]): erros.append(f"{lang} {c} {nome}: † {'sobrando' if e[1] else 'faltando'} ({t})")
                if ("‡" in t) != bool(e[2]): erros.append(f"{lang} {c} {nome}: ‡ errado ({t})")
                vals[nome] = (e[0], e[1], "rgba(200, 162, 75, 0.20)" in html)
            ok = [v for v, el, _ in vals.values() if el]
            top = max(ok) if ok else 0
            for nome, (v, el, caixa) in vals.items():
                deve = el and top > 0 and abs(v - top) < 1e-9
                conferidos["caixas de vencedor"] += 1
                if caixa != deve: erros.append(f"{lang} {c} {nome}: caixa de vencedor {'sobrando' if caixa else 'faltando'}")
        falta = {c for c in ROW if c not in vistos}
        if falta: erros.append(f"{lang}: linhas ausentes {sorted(falta)}")

    # 2. tela de recursos
    ORD = ["detector"] + FAM[:-1]
    for lang, f in (("en", "Capabilities-en"), ("pt", "Recursos-pt")):
        linhas = re.findall(r'align-items: center; height: 43px; border-bottom: 1px solid #23262f; background:[^>]*>(.*?)\n      </div>', HTML[f], re.S)
        if len(linhas) != len(ORD) + 1: erros.append(f"{lang} recursos: {len(linhas)} linhas")
        for nome, lh in zip(ORD, linhas):
            cs = [txt(x) for x in re.findall(r'<span style="text-align: center[^>]*>(.*?)</span>', lh, re.S)]
            rc = N["recursos"][nome]
            for col, idx, pct in (("onde", 0, True), ("quando", 1, True), ("alerta", 4, False), ("log", 5, False), ("incidentes", 6, True)):
                e = rc[col]; t = cs[idx]; conferidos["células de recursos"] += 1
                if col == "quando" and e is not None:
                    e = [e[0] / e[1], e[2], False]
                if e is None:
                    if t != "–": erros.append(f"{lang} recursos {nome} {col}: '{t}' esperado '–'")
                    continue
                if t == "–":
                    erros.append(f"{lang} recursos {nome} {col}: '–' esperado {e[0]}"); continue
                v = num(t.replace("%", ""), lang); ev = round(100 * e[0], 1) if pct else e[0]
                if abs(v - ev) > (0.05 if pct else 0.00051): erros.append(f"{lang} recursos {nome} {col}: {t} esperado {ev}")
                if ("†" in t) == bool(e[1]): erros.append(f"{lang} recursos {nome} {col}: † errado ({t})")
                if ("‡" in t) != bool(e[2]): erros.append(f"{lang} recursos {nome} {col}: ‡ errado ({t})")


    # 3. números citados nos textos, gerados do cálculo nos dois idiomas
    def f3(x, lang):
        s = f"{x:.3f}"; return s.replace(".", ",") if lang == "pt" else s
    def f1(x, lang):
        s = f"{x:.1f}"; return s.replace(".", ",") if lang == "pt" else s
    def milhar(x, lang):
        s = f"{x:,}"; return s.replace(",", ".") if lang == "pt" else s
    def pc(x):
        return f"{round(100 * x):g}%"
    EXTENSO = {"en": {1: "once", 2: "twice"}, "pt": {1: "uma vez", 2: "duas vezes"}}
    de = lambda lang: "of" if lang == "en" else "de"

    T = F["tetos"]; V = F["veredito"]
    m5lim = int(re.search(r"within (\d+) min", ROW["M5"]["row"]).group(1)) // 60
    cap = F.get("S3_capacidade", ["S3"])
    vit = len(V["vitorias"]) - len(cap)
    nomes_m2 = {"ddm": "DDM", "hddm_a": "HDDM", "hddm_w": "HDDM"}
    m2txt = " and ".join(dict.fromkeys(nomes_m2[k] for k in F["M2_empate"]))
    fatos = []   # (telas, en, pt)
    def fato(telas, en, pt):
        fatos.append((telas, en, pt))

    E, Pt = "en", "pt"
    s1, s2 = F["S1"], F["S2"]
    fato("S", f"{f3(s1[0], E)} event F1 · best competitor {f3(s1[1], E)}", f"{f3(s1[0], Pt)} F1 por evento · melhor concorrente {f3(s1[1], Pt)}")
    fato("S", f"{f3(s2[0], E)} event F1 · best competitor {f3(s2[1], E)}", f"{f3(s2[0], Pt)} F1 por evento · melhor concorrente {f3(s2[1], Pt)}")
    fato("S", f"{F['S3'][0]} of {F['S3'][1]}", f"{F['S3'][0]} de {F['S3'][1]}")
    if U:
        rel, ent = U["s3_por_tipo"]["relacoes"], U["s3_por_tipo"]["entradas"]
        fato("S", f"inputs {ent[1]} of {ent[0]} (ADWIN {ent[2]}) · relation breaks {rel[1]} of {rel[0]}",
             f"entradas {ent[1]} de {ent[0]} (ADWIN {ent[2]}) · quebras de relação {rel[1]} de {rel[0]}")
        fato("CR", f"{ent[0]} input changes", f"{ent[0]} mudanças de entrada")
        fato("CR", f"ADWIN {ent[2]} of {ent[0]}", f"ADWIN {ent[2]} de {ent[0]}")
        fato("R", f"the {rel[0]} relation breaks", f"as {rel[0]} quebras de relação")
        fato("C", f"{ent[0]} input changes of {rel[0] + ent[0]}", f"{ent[0]} mudanças de entrada das {rel[0] + ent[0]}")
        s7 = U["s7"]
        fato("S", f"{s7[0]} null streams and {s7[1]} shuffled copies", f"{s7[0]} séries nulas e {s7[1]} cópias embaralhadas")
        fato("R", f"({s7[0]} null, {s7[1]} shuffled", f"({s7[0]} nulas, {s7[1]} embaralhadas")
        m3 = U["m3"]
        fato("S", f"the {m3['acertos']} rest on {m3['registros_por_vida']} distinct records", f"os {m3['acertos']} vêm de {m3['registros_por_vida']} registros distintos")
        fato("R", f"{m3['acertos']} of {F['M3'][1]}, resting on {m3['registros_por_vida']} distinct records", f"{m3['acertos']} de {F['M3'][1]}, apoiados em {m3['registros_por_vida']} registros distintos")
        fato("SPR", f"{milhar(U['series'], E)} series", f"{milhar(U['series'], Pt)} séries")
    else:
        erros.append("numeros.json sem o universo (rode numeros_das_telas.py com a pasta das saídas): 2.047, S7, S3 por tipo e M3 não conferidos")
    s4a, s4b, s4c = F["S4a"], F["S4b"], F["S4c"]
    fato("S", f"{round(s4a[0] * s4a[1])} of {s4a[1]}", f"{round(s4a[0] * s4a[1])} de {s4a[1]}")
    fato("S", f"size {round(s4b[0] * s4b[1])} of {s4b[1]}", f"tamanho {round(s4b[0] * s4b[1])} de {s4b[1]}")
    rows_py = abre(os.path.join(REPO, "metrics", "rows.py")).read()
    cat = float(re.search(r'c\["value"\] == ([\d.]+) and c\["share_after"\]', rows_py).group(1))
    if U:
        n4, num4 = U["s4a"][1], U["s4a"][0]
        fato("R", f"the right answer is fixed: {num4} numeric changes go up, {n4 - num4} categorical ones raise category {cat:g}, so a constant answer also scores {f3(1, E)} · n {n4}",
             f"a resposta certa é fixa: {num4} mudanças numéricas sobem, {n4 - num4} categóricas elevam a categoria {cat:g}, então uma resposta constante também daria {f3(1, Pt)} · n {n4}")
        fato("S", f"the right answer is fixed in all {n4}", f"a resposta certa é fixa nas {n4}")
        fato("S", f"incidents tied with {m2txt}, at most {U['m2_incidentes'][1]} independent", "incidentes: empate com " + m2txt.replace(" and ", " e ") + f", no máximo {U['m2_incidentes'][1]} independentes")
    q480 = ROW["S1"]["per_method"]["detector|default"]["events"] + ROW["S2"]["per_method"]["detector|default"]["events"]
    qd, qcu = N["recursos"]["detector"]["quando"][0], N["recursos"]["cusum"]["quando"][0]
    fato("C", f"over all {q480} changes, {100 * qd / q480:.1f}% and {100 * qcu / q480:.1f}%", f"sobre todas as {q480} mudanças, {100 * qd / q480:.1f}% e {100 * qcu / q480:.1f}%".replace(".", ","))
    fato("R", f"null {f3(s4b[2], E)} · n {s4b[1]}", f"nulo {f3(s4b[2], Pt)} · n {s4b[1]}")
    fato("R", f"null {f3(s4c[2], E)} · n {s4c[1]}", f"nulo {f3(s4c[2], Pt)} · n {s4c[1]}")
    fato("S", f"{round(s4c[0] * s4c[1])} of {s4c[1]}", f"{round(s4c[0] * s4c[1])} de {s4c[1]}")
    fato("S", f"{round(s4c[2] * s4c[1])} on streams with no change", f"{round(s4c[2] * s4c[1])} em séries sem mudança")
    fato("S", f"{F['S5'][0]} of {F['S5'][1]}", f"{F['S5'][0]} de {F['S5'][1]}")
    fato("S", f"tied with {len(F['S5_empate'])} methods", f"empata com {len(F['S5_empate'])} métodos")
    a7, l7, n7 = F["S7"]
    fato("S", f"{a7} of {n7} runs with an alert · {l7} with a log", f"{a7} de {n7} rodadas com alerta · {l7} com log")
    fato("R", f"Sismo on {n7} streams with no change", f"Sismo em {n7} séries sem mudança")
    fato("R", f"alert in {a7} (ceiling {pc(T['alerta'])}), log in {l7} ({pc(T['log'])})", f"alerta em {a7} (teto {pc(T['alerta'])}), log em {l7} ({pc(T['log'])})")
    fato("R", f"alert {pc(T['alerta'])}, log {pc(T['log'])}", f"alerta {pc(T['alerta'])}, log {pc(T['log'])}")
    fato("R", f"{f1(T['publico'], E)} warnings per 1,000 items; company {f1(T['empresa'], E)}", f"{f1(T['publico'], Pt)} aviso por 1.000 itens; empresa {f1(T['empresa'], Pt)}")
    m2, m3r = F["M2"], F["M3"]
    fato("S", f"{m2[0]} of {m2[1]} · {m3r[0]} of {m3r[1]} null {m3r[2]} of {m3r[3]}", f"{m2[0]} de {m2[1]} · {m3r[0]} de {m3r[1]} nulo {m3r[2]} de {m3r[3]}")
    fato("S", f"incidents tied with {m2txt}", "incidentes: empate com " + m2txt.replace(" and ", " e "))
    fato("R", f"null {f3(m3r[2] / m3r[3], E)} · {m3r[0]} of {m3r[1]}", f"nulo {f3(m3r[2] / m3r[3], Pt)} · {m3r[0]} de {m3r[1]}")
    fato("C", f"no labels ({m2[1]})", f"não tem rótulo ({m2[1]})")
    p1 = F["P1"]
    fato("S", f"{f3(p1[0], E)} event F1 · best competitor {f3(p1[1], E)}", f"{f3(p1[0], Pt)} F1 por evento · melhor concorrente {f3(p1[1], Pt)}")
    fato("P", f"{p1[2]} of {p1[3]}", f"{p1[2]} de {p1[3]}")
    fato("P", f"its other warnings, {round(p1[4])} per 1,000 items", f"os outros avisos, {round(p1[4])} por 1.000 itens")
    tr, cb = F["publico_treino"], F["publico_combinado"]
    fato("S", f"{f1(tr[0], E)} to {f1(tr[1], E)} per 1,000 items", f"{f1(tr[0], Pt)} a {f1(tr[1], Pt)} por 1.000 itens")
    fato("S", f"{f1(cb[0], E)} to {f1(cb[1], E)}, ceiling {f1(T['publico'], E)}", f"{f1(cb[0], Pt)} a {f1(cb[1], Pt)}, teto {f1(T['publico'], Pt)}")
    m1 = F["M1"]
    fato("S", f"{m1[0]} of {m1[1]} best competitor {m1[2]} of {m1[1]}", f"{m1[0]} de {m1[1]} melhor concorrente {m1[2]} de {m1[1]}")
    fato("P", f"{m1[0]} of {m1[1]} contingencies", f"{m1[0]} de {m1[1]} contingências")
    m4 = F["M4"]
    zeros = sum(1 for v in m4["normal"] if v == 0)
    fato("S", f"{sum(1 for v in m4['normal'] if v)} of {len(m4['normal'])} normal lives", f"{sum(1 for v in m4['normal'] if v)} de {len(m4['normal'])} vidas normais")
    fato("S", f"{'one' if zeros == 1 else zeros} normal life got 0, and the life without drift also fired {EXTENSO['en'][m4['no_drift'][0]]} (must be 0)",
         f"{'uma' if zeros == 1 else zeros} vida normal deu 0, e a vida sem deriva também disparou {EXTENSO['pt'][m4['no_drift'][0]]} (devia ser 0)")
    fato("R", f"fired {EXTENSO['en'][m4['no_drift'][0]]} in the life without drift", f"disparou {EXTENSO['pt'][m4['no_drift'][0]]} na vida sem deriva")
    m5 = F["M5"]
    h0, h1 = round(m5[0] / 60), round(m5[1] / 60)
    fato("S", f"{h0} to {h1} h after recovery, {m5[2]} of {m5[3]} · the row asks {m5lim} h", f"{h0} a {h1} h depois da volta, {m5[2]} de {m5[3]} · a linha pede {m5lim} h")
    fato("R", f"confirmed {h0} to {h1} h after recovery in {m5[2]} of {m5[3]}, none within {m5lim} h · n {m5[4]}",
         f"confirmou de {h0} a {h1} h depois da volta em {m5[2]} de {m5[3]}, nenhuma em até {m5lim} h · n {m5[4]}")
    fato("P", f"{h0} to {h1} hours after the recovery", f"{h0} a {h1} horas depois da recuperação")
    fato("S", f"event F1 · best competitor {f3(F['L3'], E)}", f"F1 por evento · melhor concorrente {f3(F['L3'], Pt)}")
    p4 = F["P4L4"]
    fato("R", f"Sismo finds {p4[0]} of {p4[1]} (recall {f3(p4[2], E)}; with {milhar(p4[4], E)} false warnings its F1 there is {f3(p4[3], E)})",
         f"o Sismo acha {p4[0]} de {p4[1]} (sensibilidade {f3(p4[2], Pt)}; com {milhar(p4[4], Pt)} avisos falsos o F1 dele ali é {f3(p4[3], Pt)})")
    q, qc = N["recursos"]["detector"]["quando"], N["recursos"]["cusum"]["quando"]
    fato("C", f"Sismo {q[0]} of {q[1]}; CUSUM {qc[0]} of {qc[1]}", f"Sismo {q[0]} de {q[1]}; CUSUM {qc[0]} de {qc[1]}")
    fato("SP", f"{F['concorrentes']} competitors", f"{F['concorrentes']} concorrentes")
    fato("C", f"{F['concorrentes']} competitors", f"{F['concorrentes']} concorrentes")
    ve = (f"{V['passam']} of the {V['decidem']} rows that decide passed", f"{V['passam']} das {V['decidem']} linhas que decidem passaram")
    fato("SR", *ve)
    fato("S", f"({vit} wins, {len(cap)} by capacity, {len(V['empates'])} ties, {len(V['nulo_ou_teto'])} against a null or a ceiling)",
         f"({vit} vitórias, {len(cap)} por capacidade, {len(V['empates'])} empates, {len(V['nulo_ou_teto'])} contra um nulo ou um teto)")
    fato("R", f": {vit} wins, {len(cap)} by capacity (S3, where competitors cannot score the relation breaks), {len(V['empates'])} ties, {len(V['nulo_ou_teto'])} against a null or a ceiling",
         f": {vit} vitórias, {len(cap)} por capacidade (S3, onde os concorrentes não pontuam nas quebras de relação), {len(V['empates'])} empates, {len(V['nulo_ou_teto'])} contra nulo ou teto")

    for telas, en, pt in fatos:
        for t in telas:
            for lang, txtv in (("en", en), ("pt", pt)):
                nome = TELAS[t][0 if lang == "en" else 1]
                conferidos["números nos textos"] += 1
                if txtv not in TEXTO[nome]:
                    erros.append(f"{nome}: não achei \"{txtv}\"")

    # 4. paridade EN/PT
    def numeros(t, lang):
        t = re.sub(r"sha256 \w+", "", t); t = re.sub(r"18/10/2026|18 Oct 2026", "DATA", t)
        if lang == "pt": t = re.sub(r"(\d)\.(\d{3})", r"\1\2", t).replace(",", ".")
        else: t = re.sub(r"(\d),(\d{3})", r"\1\2", t)
        return collections.Counter(re.findall(r"\d+(?:\.\d+)?", t))
    for en, pt in TELAS.values():
        a = numeros(TEXTO[en], "en"); b = numeros(TEXTO[pt], "pt")
        conferidos["pares EN/PT"] += 1
        if a != b: erros.append(f"paridade {en}/{pt}: só em EN {dict(a - b)}, só em PT {dict(b - a)}")



try:
    _independentes()
except Exception as e:
    erros.append(f"conferência independente interrompida: {type(e).__name__}: {e}")

# 5. termos: os mesmos termos técnicos, em número igual, em cada par de telas inglês e português
TERMOS = [("warm-up", "aquecimento"), ("ceiling", "teto"), ("shuffled", "embaralhad"), ("independent", "independente"), ("approval", "aprovação"),
          ("competitor", "concorrente"), ("null", "nul"), ("alert", "alert"), ("anomal", "anomal"), ("hypothes", "hipótese"), ("adapter", "adaptador")]
for en, pt in TELAS.values():
    for a, b in TERMOS:
        conferidos["termos EN/PT"] += 1
        na, nb = TEXTO[en].lower().count(a), TEXTO[pt].lower().count(b)
        if na != nb:
            erros.append(f"termos {en}/{pt}: '{a}' aparece {na} vezes e '{b}' {nb}")
# 6. o logo
import hashlib
LOGO_SHA256 = "054647724faa9e6600a0fe2a3d3dc3f65a88c9b7841c753a60721528a2bc1a83"
conferidos["logo"] += 1
p = os.path.join(D, "marca.png")
if not os.path.exists(p) or hashlib.sha256(open(p, "rb").read()).hexdigest() != LOGO_SHA256:
    erros.append("marca.png ausente ou diferente do logo publicado")

if PARCIAL and not PUB:
    print("AUDITORIA PARCIAL (--parcial): universo não recalculado")
print("conferido:", dict(conferidos))
print("problemas:", len(erros))
for e in erros: print(" -", e)
sys.exit(1 if erros else 0)
