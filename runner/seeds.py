"""The seeds of the approval run, drawn from the frozen file after it is written (protocol, section 9).
python -m runner.seeds <frozen_file.sha256>  -> protocol/seeds.json"""
import hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
txt = open(sys.argv[1], "rb").read(); out = []; i = 0
while len(out) < 33:
    s = int(hashlib.sha256(txt + f":{i}".encode()).hexdigest()[:8], 16) % 900000 + 100000; i += 1
    if s not in out:
        out.append(s)
res = {"frozen_sha256": hashlib.sha256(txt).hexdigest(), "synthetic": out[:30], "company": out[30:33]}
json.dump(res, open(os.path.join(ROOT, "protocol", "seeds.json"), "w"), indent=1)
print(json.dumps(res))
