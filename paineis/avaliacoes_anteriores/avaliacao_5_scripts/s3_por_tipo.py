import sys,json
sys.path.insert(0,'.')
import metrics.rows as r
from collections import defaultdict
outs=[o for o in r.read('../../run/publication') if o['series']['base']=='synthetic']
bs=defaultdict(list)
for o in outs: bs[(o['series']['name'],o['series']['variant'])].append(o)
sel=lambda ss:[o for f in ss for o in bs.get((f,'main'),[])]
rel=sel(r.REL); inp=sel(r.INP)
def hit(o,k,tp):
    c=r.count(o,k[0],k[1],tp); p=c['per_event'][0]; v=set(o['series']['events'][0]['fields'])
    return p is not None and bool(p[2]) and set(p[2])<=v
D=('detector','default'); A=('adwin/field','delta=1e-06')
for nm,lst,tp in (('relações',rel,'REAL'),('entradas',inp,'VIRTUAL')):
    lst=[o for o in lst if o['series']['events'] and o['series']['events'][0]['fields']]
    print(nm,len(lst),'Sismo',sum(hit(o,D,tp) for o in lst),'ADWIN',sum(hit(o,A,tp) for o in lst))
