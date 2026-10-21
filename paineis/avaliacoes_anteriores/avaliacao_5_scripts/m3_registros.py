import json,sys,os,collections
sys.path.insert(0,'.')
import metrics.rows as r
from collections import defaultdict
a=json.load(open('../../w/rows2.json',encoding='utf-8')); b=json.load(open('results/publication/rows.json',encoding='utf-8'))
print('rows.json reproduzido idêntico:',a==b)
outs=r.read('../../run/publication'); lives='../../run/lives'
from runner.company import LATENCY_FIELD, read_truth
by_life=defaultdict(dict)
for o in outs:
    if o['series']['base']=='company' and o['series']['variant']=='main': by_life[o['series']['extra']['life']][o['series']['extra']['process']]=o
V={nv:json.load(open(os.path.join(lives,nv,'verdade.json'),encoding='utf-8')) for nv in by_life}
TR={nv:read_truth(V[nv],V[nv].get('nulo')) for nv in by_life}
DAY=1440
def te(nv,where,name):
    o=by_life[nv].get(where[0])
    if o is None or where[1] not in o['series']['field_names']: return []
    j=o['series']['field_names'].index(where[1]); return [e['t']+1 for e in o['detector']['events'] if e['field']==j and e['event']==name]
hits=[];recs=set();tot=0
for nv in by_life:
    for m in TR[nv]['regime_changes']:
        for x in m['where']:
            tot+=1
            ev=[t for t in te(nv,x,'became_new_normal') if m['t']<=t<=m['t']+15*DAY]
            if ev:
                hits.append((nv,tuple(x),m['t'],ev)); recs.add((nv,tuple(x),min(ev)))
print('M3 acertos',len(hits),'de',tot,'registros distintos',len(recs))
c=collections.Counter((nv,x,min(e)) for nv,x,t,e in hits)
print(sorted(c.values()))
for h in hits: print(h[0][:14],h[1],h[2],h[3][:3])
