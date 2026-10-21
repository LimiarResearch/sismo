"""Teste de mutação da auditoria: planta um erro por vez e exige que a auditoria o reporte.

Uso: python teste_mutacao.py <repositório> <numeros.json> <pasta com o HTML das telas> [<pasta publication> <pasta lives>]

A auditoria roda em modo --parcial (sem recalcular o universo), que é rápido; antes dos casos, o teste exige que a auditoria
sem nenhuma mutação dê 0 problemas. Com as pastas publication e lives, entra também o caso do universo adulterado, que só a
auditoria completa pega.

"Pegou" só conta quando a auditoria termina com código 1 e imprime "problemas: N" com N > 0. Se ela quebrar sem esse
relatório, o caso conta como falha do teste, não como detecção.

Casos: erros no HTML publicado (os 11 da 5ª avaliação, as 10 mutações dirigidas da 6ª e outros), um numeros.json adulterado e
um número escrito à mão num molde. Os testes exaustivos da 6ª avaliação (um número por vez em cada tela, e o mesmo número nos
dois idiomas) estão em teste_exaustivo.py.
"""
import json, os, re, shutil, subprocess, sys, tempfile

sys.stdout.reconfigure(encoding="utf-8")
REPO, NUM, SRC = [os.path.abspath(p) for p in sys.argv[1:4]]
PUB, VIDAS = ([os.path.abspath(p) for p in sys.argv[4:6]] if len(sys.argv) > 5 else (None, None))
AQUI = os.path.dirname(os.path.abspath(__file__))
TODAS = ["Capabilities-en", "Recursos-pt", "Purpose-en", "Proposito-pt", "Scorecard-en", "Placar-pt", "Results-en", "Resultados-pt"]
HTML = {  # nome: [(arquivo, antes, depois)]
    "M3 6 -> 7 registros": [("Results-en", "6 distinct", "7 distinct"), ("Resultados-pt", "6 registros", "7 registros")],
    "nulo de S4b 0,240 -> 0,340": [("Results-en", "null 0.240", "null 0.340"), ("Resultados-pt", "nulo 0,240", "nulo 0,340")],
    "F1 de P4L4 0,007 -> 0,017": [("Results-en", "F1 there is 0.007", "F1 there is 0.017"), ("Resultados-pt", "F1 dele ali é 0,007", "F1 dele ali é 0,017")],
    "veredito 2 empates -> 3, 5 -> 4 (placar)": [("Scorecard-en", "2 ties, 5 against", "3 ties, 4 against"), ("Placar-pt", "2 empates, 5 contra", "3 empates, 4 contra")],
    "veredito 2 vitórias -> 3, 1 -> 0 (tabela)": [("Results-en", "2 wins, 1 by capacity", "3 wins, 0 by capacity"), ("Resultados-pt", "2 vitórias, 1 por capacidade", "3 vitórias, 0 por capacidade")],
    "S7 180/190 -> 170/200": [("Scorecard-en", "180 null streams and 190", "170 null streams and 200"), ("Placar-pt", "180 séries nulas e 190", "170 séries nulas e 200")],
    "2.047 -> 2.147 (placar)": [("Scorecard-en", "2,047", "2,147"), ("Placar-pt", "2.047", "2.147")],
    "teto público 0,1 -> 0,2 (legenda)": [("Results-en", "0.1 warnings per 1,000", "0.2 warnings per 1,000"), ("Resultados-pt", "0,1 aviso por 1.000", "0,2 aviso por 1.000")],
    "M4 2 de 3 -> 3 de 3 (placar)": [("Scorecard-en", ">2 of 3 <", ">3 of 3 <"), ("Placar-pt", ">2 de 3 <", ">3 de 3 <")],
    "24 de 43 -> 25 de 43 só em EN": [("Purpose-en", "24 of 43", "25 of 43")],
    "71,2% -> 72,2% (recursos)": [("Capabilities-en", "71.2%", "72.2%"), ("Recursos-pt", "71,2%", "72,2%")],
    "recursos: novo normal 97,8% -> 87,8%": [("Capabilities-en", "97.8%", "87.8%"), ("Recursos-pt", "97,8%", "87,8%")],
    "recursos: direção e tamanho 100% -> 90%": [("Capabilities-en", ">100%<", ">90%<"), ("Recursos-pt", ">100%<", ">90%<")],
    "célula do Sismo em S7 0 · 6 -> 5 · 6": [("Results-en", ">0 · 6<", ">5 · 6<"), ("Resultados-pt", ">0 · 6<", ">5 · 6<")],
    "célula do Sismo em M4 2 de 3 -> 3 de 3": [("Results-en", ">2 of 3<", ">3 of 3<"), ("Resultados-pt", ">2 de 3<", ">3 de 3<")],
    "hash ed41901c -> aaaa1111 em todas": [(f, "ed41901c", "aaaa1111") for f in TODAS],
    "rótulo M1 60 min -> 90 min": [("Results-en", "route, 60 min", "route, 90 min"), ("Resultados-pt", "rota, 60 min", "rota, 90 min")],
    "até 20 campos -> 30": [("Scorecard-en", "among up to 20", "among up to 30"), ("Placar-pt", "até 20", "até 30")],
    "26 linhas -> 27 (subtítulo)": [("Results-en", "All 26 rows", "All 27 rows"), ("Resultados-pt", "As 26 linhas", "As 27 linhas")],
    "arredondamento: 0,404 -> 0,405 (L1, KSWIN)": [("Results-en", ">0.404<", ">0.405<"), ("Resultados-pt", ">0,404<", ">0,405<")],
    "cabeçalho: ADWIN e KSWIN trocados": [("Results-en", ">ADWIN<", ">@@<"), ("Results-en", ">KSWIN<", ">ADWIN<"), ("Results-en", ">@@<", ">KSWIN<")],
    "só PT: 9 de 127 -> 8 de 127": [("Resultados-pt", "9 de 127", "8 de 127")],
    "teto da empresa 0,3 -> 0,4": [("Results-en", "company 0.3", "company 0.4"), ("Resultados-pt", "empresa 0,3", "empresa 0,4")],
    "palavra: passes -> fails num veredito": [("Results-en", ">passes", ">fails")],
    "nome de método: Matrix profile -> Matrix-profile (recursos)": [("Capabilities-en", ">Matrix profile<", ">Matrix-profile<")],
    "tradução: aquecimento -> costume (placar)": [("Placar-pt", "o mesmo aquecimento", "o mesmo costume")],
    "texto sem número: 'not approved' -> 'approved'": [("Scorecard-en", ">not approved<", ">approved<")],
}


def roda(aud, src, num, extra=("--parcial",)):
    r = subprocess.run([sys.executable, "-X", "utf8", "-I", aud, REPO, num, src, *extra], capture_output=True, text=True, encoding="utf-8",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    g = re.search(r"^problemas: (\d+)", r.stdout, re.M)
    pegou = r.returncode == 1 and g is not None and int(g.group(1)) > 0
    quebrou = g is None
    linha = next((l.strip() for l in r.stdout.splitlines() if l.startswith(" -")), (r.stderr.strip().splitlines() or [""])[-1])
    return pegou, quebrou, linha


resultados = []
base = roda(os.path.join(AQUI, "auditoria.py"), SRC, NUM)
if base[0] or base[1]:
    sys.exit(f"a auditoria sem mutação não dá 0 problemas: {base[2]}")
with tempfile.TemporaryDirectory() as tmp:
    for nome, ms in HTML.items():
        w = os.path.join(tmp, "telas"); shutil.rmtree(w, ignore_errors=True); shutil.copytree(SRC, w)
        achou = True
        for f, a, b in ms:
            p = os.path.join(w, f + ".html"); t = open(p, encoding="utf-8").read()
            if a not in t: achou = False; print(f"  padrão não achado em {f}: {a}")
            open(p, "w", encoding="utf-8", newline="\n").write(t.replace(a, b))
        resultados.append((nome, achou) + roda(os.path.join(AQUI, "auditoria.py"), w, NUM))
    # numeros.json adulterado: o valor do Sismo em S1
    N = json.load(open(NUM, encoding="utf-8")); N["tabela"]["S1"]["detector"][0] = 0.5
    adult = os.path.join(tmp, "numeros_adulterado.json"); json.dump(N, open(adult, "w", encoding="utf-8"))
    resultados.append(("numeros.json adulterado (S1 do Sismo)", True) + roda(os.path.join(AQUI, "auditoria.py"), SRC, adult))
    # número escrito à mão num molde
    g = os.path.join(tmp, "gerador"); shutil.copytree(AQUI, g, ignore=shutil.ignore_patterns("telas_html", "__pycache__"))
    p = os.path.join(g, "moldes", "Scorecard-en.dc.html"); t = open(p, encoding="utf-8").read()
    open(p, "w", encoding="utf-8", newline="\n").write(t.replace("⟦s1_best⟧", "0.701", 1))
    # logo trocado
    w = os.path.join(tmp, "telas_logo"); shutil.copytree(SRC, w)
    open(os.path.join(w, "marca.png"), "ab").write(b"\0")
    resultados.append(("logo trocado", True) + roda(os.path.join(AQUI, "auditoria.py"), w, NUM))
    # auditoria sem as pastas e sem --parcial
    resultados.append(("auditoria sem publication e lives, sem --parcial", True) + roda(os.path.join(AQUI, "auditoria.py"), SRC, NUM, ()))
    # universo adulterado: só a auditoria completa pega
    if PUB:
        N = json.load(open(NUM, encoding="utf-8")); N["universo"]["series"] = 2147; N["universo"]["s7"] = [170, 200]
        adult2 = os.path.join(tmp, "numeros_universo.json"); json.dump(N, open(adult2, "w", encoding="utf-8"))
        resultados.append(("universo adulterado (séries e S7), auditoria completa", True) + roda(os.path.join(AQUI, "auditoria.py"), SRC, adult2, (PUB, VIDAS)))
    resultados.append(("molde com número escrito à mão", "0.701" in open(p, encoding="utf-8").read()) + roda(os.path.join(g, "auditoria.py"), SRC, NUM))

falhas = 0
for nome, achou, pegou, quebrou, linha in resultados:
    ok = achou and pegou
    falhas += not ok
    print(("pegou    " if ok else ("QUEBROU  " if quebrou else "NÃO PEGOU")), "|", nome, "|", linha[:120])
print(f"{len(resultados) - falhas} de {len(resultados)} erros plantados pegos")
sys.exit(1 if falhas else 0)
