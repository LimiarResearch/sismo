"""Compara os PNG de prints/ com um render novo do HTML (render_prints.mjs), pixel a pixel.

Uso: python confere_prints.py <pasta prints> <pasta do render novo>
O render das telas é determinístico (render_prints.mjs espera a rede assentar antes da captura), então qualquer pixel diferente
é um problema: o script sai com código 1 e mostra, por tela, quantos pixels diferem e onde.
"""
import os, sys
from PIL import Image, ImageChops
sys.stdout.reconfigure(encoding="utf-8")
a_dir, b_dir = sys.argv[1:3]
problemas = 0
for f in sorted(x for x in os.listdir(a_dir) if x.endswith(".png")):
    a = Image.open(os.path.join(a_dir, f)).convert("RGB")
    pb = os.path.join(b_dir, f)
    if not os.path.exists(pb):
        print(f"{f}: sem render novo"); problemas += 1; continue
    b = Image.open(pb).convert("RGB")
    if a.size != b.size:
        print(f"{f}: tamanhos diferentes {a.size} e {b.size}"); problemas += 1; continue
    d = ImageChops.difference(a, b).convert("L")
    n = sum(d.histogram()[1:])
    print(f"{f}: {n} pixels diferentes" + (f", na área {d.getbbox()}" if n else ""))
    problemas += n > 0
print("problemas:", problemas)
sys.exit(1 if problemas else 0)
