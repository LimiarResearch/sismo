import re, os, sys, shutil, subprocess, collections, tempfile
from concurrent.futures import ThreadPoolExecutor
REPO, NUM, SRC, AUD = sys.argv[1:5]
files = sorted(f for f in os.listdir(SRC) if f.endswith(".html"))
jobs = []
for f in files:
    h = open(f"{SRC}/{f}", encoding="utf-8").read()
    b = h.index("<body")
    parts = re.split(r"(<[^>]+>)", h)
    pos = 0; style = False
    for p in parts:
        start = pos; pos += len(p)
        if p.startswith("<"):
            if p.lower().startswith("<style") or p.lower().startswith("<script"): style = True
            if p.lower().startswith("</style") or p.lower().startswith("</script"): style = False
            continue
        if style or start < b: continue
        for m in re.finditer(r"\d+(?:[.,]\d+)*", p):
            jobs.append((f, start + m.start(), start + m.end(), m.group(), p))
print(len(jobs), "números em texto", file=sys.stderr)
def run(j):
    f, a, b, s, ctx = j
    d = tempfile.mkdtemp(); w = d + "/t"; shutil.copytree(SRC, w)
    h = open(f"{w}/{f}", encoding="utf-8").read()
    # troca o último dígito
    i = max(k for k, c in enumerate(s) if c.isdigit())
    n = s[:i] + str((int(s[i]) + 1) % 10) + s[i+1:]
    open(f"{w}/{f}", "w", encoding="utf-8").write(h[:a] + n + h[b:])
    r = subprocess.run([sys.executable, "-X", "utf8", "-I", AUD, REPO, NUM, w], capture_output=True, text=True, encoding="utf-8")
    shutil.rmtree(d, ignore_errors=True)
    return j, r.returncode, ("problemas:" in r.stdout)
sur = []
with ThreadPoolExecutor(8) as ex:
    for j, rc, ok in ex.map(run, jobs):
        if rc == 0 or not ok: sur.append(j)
print(len(sur), "sobreviventes")
for f, a, b, s, ctx in sur:
    i = ctx.find(s)
    print(f, "|", s, "|", ctx[max(0, i-50):i+len(s)+40].replace("\n", " "))
