import os,sys,shutil,subprocess,tempfile,re
SRC="paineis/gerador/telas_html"; AUD="paineis/gerador/auditoria.py"; NUM=os.environ['TEMP']+'/s/n.json'
PY=os.environ['TEMP']+'/venv/Scripts/python'
def t(nome, ms):
    d=tempfile.mkdtemp(); w=d+"/t"; shutil.copytree(SRC,w); ok=True
    for f,a,b,cnt in ms:
        p=f"{w}/{f}.html"; h=open(p,encoding='utf-8').read()
        if a not in h: print("  não achei",f,a); ok=False
        open(p,'w',encoding='utf-8').write(h.replace(a,b,cnt))
    r=subprocess.run([PY,"-X","utf8","-I",AUD,".",NUM,w],capture_output=True,text=True,encoding='utf-8')
    print(("PEGOU   " if r.returncode else "PASSOU  "),"|",nome,"|",[l for l in r.stdout.splitlines() if l.startswith(" -")][:1])
    shutil.rmtree(d,ignore_errors=True)
t("recursos: 97,8% (novo normal) -> 87,8% em EN e PT",[("Capabilities-en","97.8%","87.8%",1),("Recursos-pt","97,8%","87,8%",1)])
t("recursos: 100% (direção/tamanho) -> 90% em EN e PT",[("Capabilities-en",">100%<",">90%<",1),("Recursos-pt",">100%<",">90%<",1)])
t("S7 célula 0 · 6 -> 5 · 6",[("Results-en",">0 · 6<",">5 · 6<",1),("Resultados-pt",">0 · 6<",">5 · 6<",1)])
t("M4 célula 2 of 3 -> 3 of 3",[("Results-en",">2 of 3<",">3 of 3<",1),("Resultados-pt",">2 de 3<",">3 de 3<",1)])
t("hash ed41901c -> aaaa1111 (todas)",[(f,"ed41901c","aaaa1111",9) for f in ["Capabilities-en","Recursos-pt","Purpose-en","Proposito-pt","Scorecard-en","Placar-pt","Results-en","Resultados-pt"]])
t("rótulo M1 60 min -> 90 min",[("Results-en","contingency, route, 60 min","contingency, route, 90 min",1),("Resultados-pt","60 min","90 min",1)])
t("'até 20 campos' -> 30",[("Scorecard-en","among up to 20","among up to 30",1),("Placar-pt","até 20","até 30",1)])
t("'All 26 rows' -> 27 e 15->16 concorrentes (cabeçalho)",[("Results-en","All 26 rows","All 27 rows",1),("Resultados-pt","26 linhas","27 linhas",1)])
t("células 0,404 -> 0,405 (L1 kswin) EN e PT",[("Results-en",">0.404<",">0.405<",1),("Resultados-pt",">0,404<",">0,405<",1)])
t("cabeçalho: trocar ADWIN<->KSWIN (EN)",[("Results-en",">ADWIN<",">@@<",1),("Results-en",">KSWIN<",">ADWIN<",1),("Results-en",">@@<",">KSWIN<",1)])
