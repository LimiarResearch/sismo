"""The frozen file: the sha256 of every file of the benchmark that measures (code, data sources, protocol settings, environment).
python -m runner.freeze <benchmark_python> <nab_python> [htm_wheel.whl] [--name frozen_publication]
Writes protocol/ENVIRONMENT.txt and protocol/<name>.sha256 (default protocol/frozen_publication.sha256)."""
import argparse, hashlib, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ap = argparse.ArgumentParser(); ap.add_argument("python"); ap.add_argument("nab_python"); ap.add_argument("wheel", nargs="?")
ap.add_argument("--name", default="frozen_publication"); a = ap.parse_args()
env = ["# environment of the benchmark", subprocess.check_output([a.python, "-VV"], text=True).strip()]
for p, label in ((a.python, "benchmark"), (a.nab_python, "NAB score")):
    env.append(f"## {label}: " + subprocess.check_output([p, "-VV"], text=True).strip())
    for line in sorted(subprocess.check_output(["uv", "pip", "freeze", "--python", p], text=True, stderr=subprocess.DEVNULL).splitlines()):
        if line.startswith("htm @"):
            line = "htm==2.2.0 (built by data/build_htm.sh" + (f"; sha256 of the wheel {hashlib.sha256(open(a.wheel, 'rb').read()).hexdigest()})" if a.wheel else ")")
        env.append(line)
open(os.path.join(ROOT, "protocol", "ENVIRONMENT.txt"), "w").write("\n".join(env) + "\n")
# What measures goes in: the code and data folders (without documentation, the downloaded data and the generated lives), the protocol
# settings and the environment. Documentation (*.md files, the top-level README, NOTICE and licenses), scripts that only check
# (reproduce.sh, the publication comparison tools) and outputs do not.
FOLDERS = ("detector", "competitors", "runner", "metrics", "generators", "data")
FILES = ("protocol/ENVIRONMENT.txt", "protocol/cjsd_default.json", "protocol/tuned.json", "protocol/seeds.json",
         "protocol/publication/keymap.json", "requirements.txt", "requirements-nab.txt")
rels = [r for r in FILES if os.path.exists(os.path.join(ROOT, r))]
for p in FOLDERS:
    for root, dirs, files in os.walk(os.path.join(ROOT, p)):
        dirs[:] = sorted(d for d in dirs if d not in ("__pycache__", "raw", "lives"))
        rels += [os.path.relpath(os.path.join(root, f), ROOT) for f in sorted(files) if not f.endswith((".pyc", ".md"))]
lines = [f"{hashlib.sha256(open(os.path.join(ROOT, r), 'rb').read()).hexdigest()}  {r}" for r in sorted(rels)]
open(os.path.join(ROOT, "protocol", a.name + ".sha256"), "w").write("\n".join(lines) + "\n")
print(len(lines), "files;", hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest())
