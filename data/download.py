"""Downloads the public data of the benchmark and checks the sha256 of each file against data/sources.json.
python data/download.py [destination] [--bases nab,smd,smap_msl,nab_code,label_check]
  destination  default data/raw
  --bases      default: all of them (nab, smd, smap_msl: the data; nab_code: the NAB scoring code used by metrics/nab_score.py;
               label_check: the original SMAP and MSL labels, to check the copy that comes with smap_msl)
Nothing is redistributed by this package: each file comes from its pinned origin (repository and commit, or official address)."""
import hashlib, json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ALL_BASES = ("nab", "smd", "smap_msl", "nab_code", "label_check")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def download(dest, bases):
    sources = json.load(open(os.path.join(HERE, "sources.json"), encoding="utf-8"))["files"]
    unknown = set(bases) - {a["base"] for a in sources}
    if unknown:
        raise SystemExit(f"unknown bases: {', '.join(sorted(unknown))} (known: {', '.join(ALL_BASES)})")
    ok = new = 0
    for a in sources:
        if a["base"] not in bases:
            continue
        p = os.path.join(dest, a["path"])
        if not (os.path.exists(p) and sha256(p) == a["sha256"]):
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with urllib.request.urlopen(a["origin"], timeout=600) as r, open(p + ".partial", "wb") as f:
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    f.write(b)
            os.replace(p + ".partial", p); new += 1
        h = sha256(p)
        if h != a["sha256"]:
            raise SystemExit(f"different sha256 in {a['path']}: {h} (expected {a['sha256']})")
        ok += 1
    print(f"{ok} files checked ({new} downloaded now) in {dest}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    bases = set(ALL_BASES)
    if "--bases" in sys.argv:
        bases = set(sys.argv[sys.argv.index("--bases") + 1].split(","))
        args = [a for a in args if a != sys.argv[sys.argv.index("--bases") + 1]]
    download(args[0] if args else os.path.join(HERE, "raw"), bases)
