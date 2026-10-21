import re, os, sys, shutil, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor
REPO, NUM, SRC, AUD = sys.argv[1:5]
PAIRS=[("Capabilities-en","Recursos-pt"),("Purpose-en","Proposito-pt"),("Scorecard-en","Placar-pt"),("Results-en","Resultados-pt")]
def toks(f,lang):
    h=open(f"{SRC}/{f}.html",encoding="utf-8").read(); b=h.index("<body")
    parts=re.split(r"(<[^>]+>)",h); pos=0; st=False; out=[]
    for p in parts:
        s=pos; pos+=len(p)
        if p.startswith("<"):
            l=p.lower()
            if l.startswith(("<style","<script")): st=True
            if l.startswith(("</style","</script")): st=False
            continue
        if st or s<b: continue
        for m in re.finditer(r"\d+(?:[.,]\d+)*",p):
            t=m.group(); n=t
            if lang=="pt": n=t.replace(".","").replace(",",".") if re.search(r",\d",t) or re.fullmatch(r"\d{1,3}(\.\d{3})+",t) else t
            else: n=t.replace(",","") if re.fullmatch(r"\d{1,3}(,\d{3})+",t) else t
            out.append((s+m.start(),s+m.end(),t,n))
    return out
def bump(t):
    i=max(k for k,c in enumerate(t) if c.isdigit()); return t[:i]+str((int(t[i])+1)%10)+t[i+1:]
jobs=[]
for en,pt in PAIRS:
    a,b=toks(en,"en"),toks(pt,"pt")
    import difflib
    sm=difflib.SequenceMatcher(None,[x[3] for x in a],[x[3] for x in b],autojunk=False)
    for blk in sm.get_matching_blocks():
        for q in range(blk.size): jobs.append((en,pt,a[blk.a+q],b[blk.b+q]))
    continue
    if False:
        print("sequências diferem",en,len(a),len(b)); 
        # tenta alinhar por multiconjunto: ignora
        continue
    for i,(x,y) in enumerate(zip(a,b)): jobs.append((en,pt,x,y))
print(len(jobs),"pares alinhados",file=sys.stderr)
def run(j):
    en,pt,x,y=j
    d=tempfile.mkdtemp(); w=d+"/t"; shutil.copytree(SRC,w)
    for f,z in ((en,x),(pt,y)):
        h=open(f"{w}/{f}.html",encoding="utf-8").read()
        open(f"{w}/{f}.html","w",encoding="utf-8").write(h[:z[0]]+bump(z[2])+h[z[1]:])
    r=subprocess.run([sys.executable,"-X","utf8","-I",AUD,REPO,NUM,w],capture_output=True,text=True,encoding="utf-8")
    shutil.rmtree(d,ignore_errors=True)
    return j,r
sur=[]
with ThreadPoolExecutor(8) as ex:
    for j,r in ex.map(run,jobs):
        if r.returncode==0: sur.append(j)
        elif "problemas:" not in r.stdout: sur.append(("CRASH",)+j)
print(len(sur),"sobreviventes")
h={f:open(f"{SRC}/{f}.html",encoding="utf-8").read() for p in PAIRS for f in p}
for j in sur:
    tag=""
    if j[0]=="CRASH": tag="CRASH "; j=j[1:]
    en,pt,x,y=j
    c=h[en]; print(tag+en,"|",x[2],"|",re.sub(r"<[^>]+>"," ",c[max(0,x[0]-90):x[1]+50]).replace("\n"," ")[-110:])
