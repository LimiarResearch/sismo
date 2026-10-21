"""Teste exaustivo da auditoria, a partir dos scripts da 6ª avaliação independente (avaliacoes_anteriores/avaliacao_6_scripts/).

Uso: python teste_exaustivo.py <repositório> <numeros.json> <pasta com o HTML das telas>

1. um idioma: troca o último dígito de cada número do texto visível de cada tela, um por vez;
2. pares: troca o mesmo número nas duas versões (inglês e português) da mesma tela ao mesmo tempo, que é o caso que a
   paridade entre idiomas não pega.
Cada mutação tem de terminar com a auditoria em código 1 e "problemas: N" com N > 0. Uma quebra sem relatório conta como falha.
"""
import difflib, os, re, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8")
REPO, NUM, SRC = [os.path.abspath(p) for p in sys.argv[1:4]]
AUD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auditoria.py")
PARES = [("Capabilities-en", "Recursos-pt"), ("Purpose-en", "Proposito-pt"), ("Scorecard-en", "Placar-pt"), ("Results-en", "Resultados-pt")]


def tokens(nome, lang):
    h = open(f"{SRC}/{nome}.html", encoding="utf-8").read(); b = h.index("<body")
    pos = 0; dentro = False; out = []
    for p in re.split(r"(<[^>]+>)", h):
        s = pos; pos += len(p)
        if p.startswith("<"):
            l = p.lower()
            if l.startswith(("<style", "<script")): dentro = True
            if l.startswith(("</style", "</script")): dentro = False
            continue
        if dentro or s < b: continue
        for g in re.finditer(r"\d+(?:[.,]\d+)*", p):
            t = g.group()
            if lang == "pt":
                n = t.replace(".", "").replace(",", ".") if re.search(r",\d", t) or re.fullmatch(r"\d{1,3}(\.\d{3})+", t) else t
            else:
                n = t.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+", t) else t
            out.append((s + g.start(), s + g.end(), t, n))
    return out


def troca(t):
    i = max(k for k, c in enumerate(t) if c.isdigit()); return t[:i] + str((int(t[i]) + 1) % 10) + t[i + 1:]


def roda(mudancas):
    d = tempfile.mkdtemp(); w = os.path.join(d, "t"); shutil.copytree(SRC, w)
    try:
        for nome, (a, b, t, _) in mudancas:
            p = f"{w}/{nome}.html"; h = open(p, encoding="utf-8").read()
            open(p, "w", encoding="utf-8", newline="\n").write(h[:a] + troca(t) + h[b:])
        r = subprocess.run([sys.executable, "-X", "utf8", "-I", AUD, REPO, NUM, w, "--parcial"], capture_output=True, text=True, encoding="utf-8",
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        g = re.search(r"^problemas: (\d+)", r.stdout, re.M)
        return r.returncode == 1 and g is not None and int(g.group(1)) > 0
    finally:
        shutil.rmtree(d, ignore_errors=True)


r0 = subprocess.run([sys.executable, "-X", "utf8", "-I", AUD, REPO, NUM, SRC, "--parcial"], capture_output=True, text=True, encoding="utf-8")
if r0.returncode != 0:
    sys.exit("a auditoria sem mutação não dá 0 problemas: " + r0.stdout[-300:])
casos = {"um idioma": [], "pares": []}
for en, pt in PARES:
    a, b = tokens(en, "en"), tokens(pt, "pt")
    casos["um idioma"] += [[(en, x)] for x in a] + [[(pt, y)] for y in b]
    sm = difflib.SequenceMatcher(None, [x[3] for x in a], [y[3] for y in b], autojunk=False)
    for blk in sm.get_matching_blocks():
        casos["pares"] += [[(en, a[blk.a + q]), (pt, b[blk.b + q])] for q in range(blk.size)]
falhas = 0
for nome, lista in casos.items():
    with ThreadPoolExecutor(8) as ex:
        ok = list(ex.map(roda, lista))
    sobr = [c for c, o in zip(lista, ok) if not o]
    falhas += len(sobr)
    print(f"{nome}: {len(lista)} mutações, {len(sobr)} sobreviventes")
    for c in sobr[:20]:
        print("   ", " + ".join(f"{n} '{t[2]}'" for n, t in c))
sys.exit(1 if falhas else 0)
