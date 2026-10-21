import shutil,subprocess,os,re,sys
SRC='paineis/gerador/telas_html'; W='../../w/mut'
muts={
 'M3 6->7 registros (EN+PT)':[('Results-en.html','6 distinct','7 distinct'),('Resultados-pt.html','6 registros','7 registros')],
 'S4b null 0.240->0.340':[('Results-en.html','null 0.240','null 0.340'),('Resultados-pt.html','nulo 0,240','nulo 0,340')],
 'P4L4 F1 0.007->0.017':[('Results-en.html','F1 there is 0.007','F1 there is 0.017'),('Resultados-pt.html','F1 dele ali é 0,007','F1 dele ali é 0,017')],
 'veredito 2 ties->3 ties/4':[('Scorecard-en.html','2 ties, 5 against','3 ties, 4 against'),('Placar-pt.html','2 empates, 5 contra','3 empates, 4 contra')],
 'verdito 2 wins->3 wins/0 capacity (Results)':[('Results-en.html','2 wins, 1 by capacity','3 wins, 0 by capacity'),('Resultados-pt.html','2 vitórias, 1 por capacidade','3 vitórias, 0 por capacidade')],
 '180/190 -> 170/200':[('Scorecard-en.html','180 null streams and 190','170 null streams and 200'),('Placar-pt.html','180 séries nulas e 190','170 séries nulas e 200')],
 '2,047 -> 2,147':[('Scorecard-en.html','2,047','2,147'),('Placar-pt.html','2.047','2.147')],
 'teto publico 0.1 -> 0.2 legenda':[('Results-en.html','0.1 warnings per 1,000','0.2 warnings per 1,000'),('Resultados-pt.html','0,1 aviso por 1.000','0,2 aviso por 1.000')],
 'M4 2 of 3 -> 3 of 3 (EN+PT)':[('Scorecard-en.html','>2 of 3 <','>3 of 3 <'),('Placar-pt.html','>2 de 3 <','>3 de 3 <')],
 'Purpose 24 of 43 -> 25 of 43 so EN':[('Purpose-en.html','24 of 43','25 of 43')],
 'Capabilities 71.2% -> 72.2% (EN+PT)':[('Capabilities-en.html','71.2%','72.2%'),('Recursos-pt.html','71,2%','72,2%')],
}
for name,ms in muts.items():
    shutil.rmtree(W,ignore_errors=True); shutil.copytree(SRC,W)
    ok=True
    for f,a,b in ms:
        p=f'{W}/{f}'; t=open(p,encoding='utf-8').read()
        n=t.count(a)
        if n==0: ok=False; print('  !! padrão não achado',f,a)
        open(p,'w',encoding='utf-8').write(t.replace(a,b))
    r=subprocess.run([sys.executable,'-I','-X','utf8','paineis/gerador/auditoria.py','results/publication/rows.json','../../w/n.json',W],capture_output=True,text=True,encoding='utf-8')
    probs=[l for l in r.stdout.splitlines() if l.startswith(' -')]
    print(('PEGOU ' if probs else 'NÃO PEGOU'),'|',name,'|',probs[:1] if probs else r.stdout.splitlines()[-1:])
