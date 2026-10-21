import json,sys,runpy
sys.argv=['x','results/publication/rows.json']
g=runpy.run_path('paineis/gerador/numeros_das_telas.py')
ROW=g['ROW']; el=g['elegivel']; M=g['METRICA']
for c in g['COM_CONCORRENTE']:
    pm=ROW[c]['per_method']
    # competidores permitidos no S3/P4o: só os que nomeiam campo
    cand=[(d[M[c]],k) for k,d in pm.items() if k!='detector|default' and el(c,k) and d[M[c]] is not None]
    if c=='S3':
        pass
    mx=max(cand)[0] if cand else None
    rb=ROW[c]['best_value']
    flag='' if (mx==rb or (mx is not None and rb is not None and abs(mx-rb)<1e-12)) else '  <<< DIFERE'
    print(f"{c:5s} gerador {mx} rows.json {rb} {ROW[c]['best_competitor'] and ROW[c]['best_competitor'][:40]}{flag}")
    # os elegíveis do gerador incluem algum que o rows.py não aceitaria (S3/P4o names_field)?
    if c=='S3': print('   S3 configs',sorted({k.split('|')[0] for k in pm}))
    if c=='P4o': print('   P4o configs',sorted({k.split('|')[0] for k in pm}))
    if c in('M1','M2'): print('   familias',sorted({k.split('|')[0] for k in pm}))
