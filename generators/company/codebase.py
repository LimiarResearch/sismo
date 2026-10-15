"""The product code. Routes call functions; each function has one or more implementations written here, the ones that already
existed and the ones that will exist. A product version is the choice of one implementation per function; a commit swaps the
implementation of a function; releasing puts another choice on the server.

Some implementations have a defect, and the defect is genuinely wrong code: a text conversion that breaks on accented characters,
an index that runs past the end of a list, a check dropped in a refactoring, a query that loads the whole table. When the route
runs with that implementation the exception happens (or the write is doubled, or the query is heavy), and that is what the metrics
measure. Nothing here draws errors at random. Other implementations are new features: they do more (or less) work and change the
route's normal behavior.

The implementation functions are named <function>__<variant>, and the function and variant names are part of the recorded data
(ground truth, test results), so they stay in Portuguese. Quality's tests also live here: they call the routes in a test
environment and check the result."""
import re
import unicodedata

from .catalog import DIGIT_REGION


class Recusa(Exception):
    """The user's request cannot be served under the business rules (out of stock, card declined, already paid). Not a code error.
    ("Recusa" means refusal; the class name is kept because it can appear in recorded test-failure messages.)"""


PROCESS_ROW_LIMIT = 40000      # the application process cannot build a list larger than this in one request
SHIPPING_TABLE = {"0": (1, 18.0), "1": (1, 19.0), "2": (2, 22.0), "3": (1, 16.0), "4": (4, 31.0), "5": (5, 34.0), "6": (6, 39.0),
                "7": (4, 29.0), "8": (3, 24.0), "9": (3, 26.0)}
TAX_RATE_BY_STATE = {"SP": 0.18, "RJ": 0.20, "ES": 0.17, "MG": 0.18, "PR": 0.195, "SC": 0.17, "RS": 0.17, "BA": 0.205, "SE": 0.19,
               "PE": 0.205, "AL": 0.19, "PB": 0.20, "RN": 0.20, "CE": 0.20, "PI": 0.21, "MA": 0.22, "PA": 0.19, "AM": 0.20,
               "AP": 0.18, "RR": 0.20, "AC": 0.19, "DF": 0.20, "GO": 0.19, "TO": 0.20, "MT": 0.17, "MS": 0.17, "RO": 0.195}
# the table introduced by a refactoring of the tax calculation: only the states of the South and Southeast
TAX_RATE_SOUTH_SOUTHEAST = {uf: TAX_RATE_BY_STATE[uf] for uf in ("SP", "RJ", "ES", "MG", "PR", "SC", "RS")}


def _strip_accents(text):
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


# ======================================================================================================== login and account
def normalizar_login__correta(login):
    return unicodedata.normalize("NFC", login).strip().lower()


def normalizar_login__ascii(login):
    return login.strip().encode("ascii").decode("ascii").lower()


def verificar_senha__simples(x, user):
    x.work(4)


def verificar_senha__reforcada(x, user):
    x.work(320)                                      # many more rounds in the password derivation


def registrar_dispositivo__nada(x, user):
    return None


def registrar_dispositivo__grava(x, user):
    n = x.db.fetch_one("SELECT COUNT(*) FROM dispositivos WHERE usuario=?", (user,))[0]
    if not x.simulated:
        x.db.exe("INSERT INTO dispositivos (usuario, t) VALUES (?,?)", (user, x.t))
    x.work(160 + n // 4)                             # computes the device fingerprint and compares it with previous ones


def guardar_sessao__com_expiracao(cache, token, user, t):
    cache[token] = (user, t)
    while cache:
        oldest_token = next(iter(cache))
        if cache[oldest_token][1] >= t - 120:
            break
        del cache[oldest_token]


def guardar_sessao__sem_expiracao(cache, token, user, t):
    cache[token] = (user, t)


def atualizar_conta__correta(x, customer, data):
    phone = (data.get("telefone") or "").strip()
    name = (data.get("nome_fantasia") or "").strip()
    if not x.simulated:
        x.db.exe("UPDATE clientes SET telefone=?, nome_fantasia=? WHERE id=?", (phone or None, name or None, customer))


def atualizar_conta__telefone(x, customer, data):
    phone = data["telefone"].strip().replace(" ", "")        # assumes every customer has a phone number
    name = (data.get("nome_fantasia") or "").strip()
    if not x.simulated:
        x.db.exe("UPDATE clientes SET telefone=?, nome_fantasia=? WHERE id=?", (phone, name or None, customer))


# ======================================================================================================== catalog and search
def listar_produtos__pagina_20(x, category):
    return x.db.fetch_all("SELECT id, nome, preco, estoque FROM produtos WHERE categoria=? ORDER BY nome", (category,)), 20


def listar_produtos__pagina_40(x, category):
    rows = x.db.fetch_all("SELECT id, nome, preco, estoque, peso, vendidos FROM produtos WHERE categoria=? ORDER BY nome", (category,))
    x.work(len(rows) // 3)
    return rows, 40


def paginar__correta(rows, page, size):
    start = (page - 1) * size
    return rows[start:start + size], page * size < len(rows)


def paginar__ultima_pagina(rows, page, size):
    start = (page - 1) * size
    page_slice = rows[start:start + size]
    cursor = rows[page * size - 1][0]               # the cursor of the next page; it does not exist on an incomplete last page
    return page_slice, cursor < rows[-1][0] or page * size < len(rows)


def recomendar__nenhuma(x, customer):
    return []


def recomendar__historico(x, customer):
    rows = x.db.fetch_all("SELECT i.produto, SUM(i.quantidade) AS q FROM pedidos p JOIN itens_pedido i ON i.pedido = p.id "
                        "WHERE p.cliente=? AND p.t>? GROUP BY i.produto ORDER BY q DESC LIMIT 8", (customer, x.t - 30 * 1440))
    x.work(60)
    return rows


def recomendar__historico_curto(x, customer):
    rows = x.db.fetch_all("SELECT i.produto, SUM(i.quantidade) AS q FROM pedidos p JOIN itens_pedido i ON i.pedido = p.id "
                        "WHERE p.cliente=? AND p.t>? GROUP BY i.produto ORDER BY q DESC LIMIT 4", (customer, x.t - 7 * 1440))
    x.work(15)
    return rows


def normalizar_termo__correta(term):
    return _strip_accents(term.lower()).strip()


def normalizar_termo__ascii(term):
    return term.lower().encode("ascii").decode("ascii").strip()


def buscar_produtos__varredura(x, term):
    hits = x.db.fetch_all("SELECT id, nome, preco FROM produtos WHERE nome_busca LIKE ? LIMIT 30", ("%" + term + "%",))
    x.work(140)                                      # ranks by similarity, comparing the term with the whole catalog
    return hits


def buscar_produtos__indice(x, term):
    word = term.split()[0]
    hits = x.db.fetch_all("SELECT p.id, p.nome, p.preco FROM palavras w JOIN produtos p ON p.id = w.produto "
                         "WHERE w.palavra >= ? AND w.palavra < ? LIMIT 30", (word, word + "\uffff"))
    x.work(10)
    return hits


def buscar_produtos__sinonimos(x, term):
    hits = x.db.fetch_all("SELECT id, nome, preco FROM produtos WHERE nome_busca LIKE ? LIMIT 30", ("%" + term + "%",))
    for synonym in SYNONYMS.get(term.split()[0], ()):
        hits += x.db.fetch_all("SELECT id, nome, preco FROM produtos WHERE nome_busca LIKE ? LIMIT 10", ("%" + synonym + "%",))
    x.work(25)
    return hits


SYNONYMS = {"refrigerante": ("guarana", "cola"), "biscoito": ("bolacha",), "bolacha": ("biscoito",), "sabao": ("detergente",),
             "detergente": ("sabao",), "papel": ("guardanapo",), "cafe": ("capsula",), "arroz": ("graos",)}


def detalhar_produto__simples(x, product):
    p = x.db.fetch_one("SELECT id, nome, preco, estoque, categoria FROM produtos WHERE id=?", (product,))
    if p is None:
        raise Recusa("produto inexistente")
    return p


def detalhar_produto__relacionados(x, product):
    p = x.db.fetch_one("SELECT id, nome, preco, estoque, categoria FROM produtos WHERE id=?", (product,))
    if p is None:
        raise Recusa("produto inexistente")
    related = x.db.fetch_all("SELECT id, nome, preco FROM produtos WHERE categoria=? AND id<>? ORDER BY vendidos DESC LIMIT 6", (p[4], product))
    x.work(30)
    return p, related


# ======================================================================================================== order and cart
def ler_quantidade__correta(text):
    q = int(text)
    if q < 1 or q > 999:
        raise Recusa("quantidade fora do limite")
    return q


def ler_quantidade__um_digito(text):
    return int(re.fullmatch(r"[1-9]", text.strip()).group(0))   # the new input mask only accepts one digit


def reservar_estoque__correta(x, items):
    prices = []
    for product, q in items:
        p = x.db.fetch_one("SELECT preco, estoque FROM produtos WHERE id=?", (product,))
        if p is None:
            raise Recusa("produto inexistente")
        if p[1] < q:
            raise Recusa("sem estoque")
        prices.append(p[0])
    if not x.simulated:
        for product, q in items:
            x.db.exe("UPDATE produtos SET estoque = estoque - ?, vendidos = vendidos + ? WHERE id=?", (q, q, product))
    return prices


def verificar_fraude__nada(x, customer):
    return True


def verificar_fraude__antifraude(x, customer):
    recent = x.db.fetch_one("SELECT COUNT(*), COALESCE(SUM(valor), 0) FROM pedidos WHERE cliente=? AND t>?", (customer, x.t - 1440))
    x.external(x.product.antifraud.lookup())
    x.work(20)
    return recent[0] < 200


# ======================================================================================================== shipping
def calcular_frete__correta(cep):
    digits = cep.replace("-", "").strip()
    if len(digits) != 8 or not digits.isdigit():
        raise Recusa("CEP inválido")
    return SHIPPING_TABLE[digits[0]]


def calcular_frete__numerico(cep):
    number = int(cep.replace("-", ""))
    text = str(number)
    if len(text) != 8:                                     # the leading zero is lost in the conversion to a number
        raise ValueError("CEP inválido: " + text)
    return SHIPPING_TABLE[text[0]]


def cotar_transportadoras__uma(x, region, weight):
    x.external(x.product.carriers.quote())
    return region[1] + 2.5 * weight


def cotar_transportadoras__duas(x, region, weight):
    a = x.product.carriers.quote()
    b = x.product.carriers.quote()
    x.external(max(a, b) + 40.0)
    x.work(10)
    return min(region[1] + 2.5 * weight, region[1] * 0.92 + 2.8 * weight)


# ======================================================================================================== payment
def autenticar_pagamento__direto(x):
    return True


def autenticar_pagamento__tres_ds(x):
    x.external(x.product.gateway.authenticate())
    x.work(12)
    return True


def registrar_cobranca__correta(x, order, value):
    if x.db.fetch_one("SELECT 1 FROM pagamentos WHERE pedido=? AND estado<>'recusado'", (order,)) is not None:
        raise Recusa("pedido já pago")
    return x.db.exe("INSERT INTO pagamentos (pedido, valor, estado, t) VALUES (?,?,?,?)", (order, value, "pendente", x.t)).lastrowid


def registrar_cobranca__sem_verificacao(x, order, value):
    return x.db.exe("INSERT INTO pagamentos (pedido, valor, estado, t) VALUES (?,?,?,?)", (order, value, "pendente", x.t)).lastrowid


# ======================================================================================================== fiscal
def emitir_nota__correta(x, order):
    p = x.db.fetch_one("SELECT p.cliente, p.valor, c.uf FROM pedidos p JOIN clientes c ON c.id = p.cliente WHERE p.id=?", (order,))
    tax = round(p[1] * TAX_RATE_BY_STATE[p[2]], 2)
    x.db.exe("INSERT INTO notas (pedido, cliente, uf, valor, imposto, estado, t) VALUES (?,?,?,?,?,?,?)",
             (order, p[0], p[2], p[1], tax, "emitida", x.t))


def emitir_nota__aliquota_regional(x, order):
    p = x.db.fetch_one("SELECT p.cliente, p.valor, c.uf FROM pedidos p JOIN clientes c ON c.id = p.cliente WHERE p.id=?", (order,))
    tax = round(p[1] * TAX_RATE_SOUTH_SOUTHEAST[p[2]], 2)
    x.db.exe("INSERT INTO notas (pedido, cliente, uf, valor, imposto, estado, t) VALUES (?,?,?,?,?,?,?)",
             (order, p[0], p[2], p[1], tax, "emitida", x.t))


def listar_notas__todas(x, customer):
    fiscal_notes = x.db.fetch_all("SELECT id, pedido, valor, imposto, estado, t FROM notas WHERE cliente=? ORDER BY t DESC", (customer,))
    x.work(len(fiscal_notes) // 2)                          # builds the page with all of the customer's fiscal notes
    return fiscal_notes


def listar_notas__paginada(x, customer):
    return x.db.fetch_all("SELECT id, valor, imposto, t FROM notas WHERE cliente=? ORDER BY t DESC LIMIT 20", (customer,))


# ======================================================================================================== reports
def montar_relatorio__filtrado(x, customer, since):
    rows = x.db.fetch_all("SELECT valor, itens, t FROM pedidos WHERE cliente=? AND t>=?", (customer, since))
    x.work(5 + len(rows) // 4)
    return sum(v for v, _, _ in rows)


def montar_relatorio__por_item(x, customer, since):
    rows = x.db.fetch_all("SELECT i.produto, SUM(i.quantidade), SUM(i.quantidade * i.preco) FROM pedidos p "
                        "JOIN itens_pedido i ON i.pedido = p.id WHERE p.cliente=? AND p.t>=? GROUP BY i.produto", (customer, since))
    x.work(40 + len(rows))
    return sum(v for _, _, v in rows)


def montar_relatorio__sem_filtro(x, customer, since):
    cursor = x.db.cursor("SELECT cliente, valor, itens, t FROM pedidos")    # fetches every order and filters here
    rows = []
    while True:
        block = cursor.fetchmany(2000)
        if not block:
            break
        rows.extend(block)
        if len(rows) > PROCESS_ROW_LIMIT:
            raise MemoryError("relatório não cabe na memória do processo")
    x.work(len(rows) // 8)
    return sum(v for c, v, _, t in rows if c == customer and t >= since)


def exportar_csv__lote(x, customer, since):
    rows = x.db.fetch_all("SELECT p.id, p.valor, i.produto, i.quantidade FROM pedidos p JOIN itens_pedido i ON i.pedido = p.id "
                        "WHERE p.cliente=? AND p.t>=?", (customer, since))
    x.work(10 + len(rows) // 3)
    return len(rows)


def exportar_csv__compactada(x, customer, since):
    rows = x.db.fetch_all("SELECT p.id, p.valor, i.produto, i.quantidade FROM pedidos p JOIN itens_pedido i ON i.pedido = p.id "
                        "WHERE p.cliente=? AND p.t>=?", (customer, since))
    x.work(80 + len(rows))                             # compresses the file before delivering it
    return len(rows)


def exportar_csv__n_mais_um(x, customer, since):
    orders = x.db.fetch_all("SELECT id, valor FROM pedidos WHERE cliente=? AND t>=?", (customer, since))
    total = 0
    for pid, _ in orders:                                   # one query per order
        total += len(x.db.fetch_all("SELECT produto, quantidade FROM itens_pedido WHERE pedido=?", (pid,)))
    x.work(10 + total // 3)
    return total


# ======================================================================================================== notifications
def enviar_email__correta(x, customer, kind):
    c = x.db.fetch_one("SELECT nome_fantasia, razao FROM clientes WHERE id=?", (customer,))
    subject = f"{(c[0] or c[1])}: {kind}"
    x.db.exe("INSERT INTO emails (cliente, tipo, assunto, t) VALUES (?,?,?,?)", (customer, kind, subject, x.t))


def enviar_email__nome_fantasia(x, customer, kind):
    c = x.db.fetch_one("SELECT nome_fantasia, razao FROM clientes WHERE id=?", (customer,))
    subject = f"{c[0].title()}: {kind}"                     # the new template only uses the trade name
    x.db.exe("INSERT INTO emails (cliente, tipo, assunto, t) VALUES (?,?,?,?)", (customer, kind, subject, x.t))


# ======================================================================================================== routes
def route_login(x, r):
    login = x.cod["normalizar_login"](r["login"])
    u = x.db.fetch_one("SELECT id, cliente FROM usuarios WHERE login=? AND ativo=1", (login,))
    if u is None:
        raise Recusa("usuário ou senha inválidos")
    x.cod["verificar_senha"](x, u[0])
    x.cod["registrar_dispositivo"](x, u[0])
    if not x.simulated:
        token = x.product.new_token()
        x.db.exe("INSERT INTO sessoes (token, usuario, criada_em) VALUES (?,?,?)", (token, u[0], x.t))
        x.cod["guardar_sessao"](x.product.session_cache, token, u[0], x.t)
    return u[0]


def route_catalog(x, r):
    rows, size = x.cod["listar_produtos"](x, r["categoria"])
    page, _ = x.cod["paginar"](rows, r.get("pagina", 1), size)
    recommended = x.cod["recomendar"](x, x.customer)
    x.work(len(page) // 4 + len(recommended))
    return len(page)


def route_search(x, r):
    term = x.cod["normalizar_termo"](r["termo"])
    if not term:
        raise Recusa("termo vazio")
    hits = x.cod["buscar_produtos"](x, term)
    x.work(2 + len(hits) // 5)
    return len(hits)


def route_product(x, r):
    return x.cod["detalhar_produto"](x, r["produto"])


def route_cart(x, r):
    q = x.cod["ler_quantidade"](r["quantidade"])
    p = x.db.fetch_one("SELECT preco FROM produtos WHERE id=?", (r["produto"],))
    if p is None:
        raise Recusa("produto inexistente")
    if not x.simulated:
        x.db.exe("INSERT INTO carrinhos (usuario, produto, quantidade, t) VALUES (?,?,?,?)", (x.user, r["produto"], q, x.t))
    return q * p[0]


def route_shipping(x, r):
    region = x.cod["calcular_frete"](r["cep"])
    return x.cod["cotar_transportadoras"](x, region, r.get("peso", 1.0))


def route_order(x, r):
    items = [(product, x.cod["ler_quantidade"](text)) for product, text in r["itens"]]
    region = x.cod["calcular_frete"](r["cep"])
    x.cod["verificar_fraude"](x, x.customer)
    prices = x.cod["reservar_estoque"](x, items)
    value = round(sum(p * q for p, (_, q) in zip(prices, items)) + region[1], 2)
    if x.simulated:
        return None
    pid = x.db.exe("INSERT INTO pedidos (cliente, usuario, valor, itens, estado, cep, t) VALUES (?,?,?,?,?,?,?)",
                   (x.customer, x.user, value, len(items), "criado", r["cep"], x.t)).lastrowid
    for (product, q), price in zip(items, prices):
        x.db.exe("INSERT INTO itens_pedido (pedido, produto, quantidade, preco) VALUES (?,?,?,?)", (pid, product, q, price))
    x.db.exe("DELETE FROM carrinhos WHERE usuario=?", (x.user,))
    x.product.enqueue("nota", pid, x.t)
    x.product.enqueue("email", x.customer, x.t)
    x.work(3 + len(items))
    return pid, value


def route_payment(x, r):
    order_row = x.db.fetch_one("SELECT id, valor FROM pedidos WHERE id=?", (r["pedido"],))
    if order_row is None:
        raise Recusa("pedido inexistente")
    x.cod["autenticar_pagamento"](x)
    if x.simulated:
        x.external(x.product.gateway.lookup())
        return None
    payment = x.cod["registrar_cobranca"](x, order_row[0], order_row[1])
    approved, wait = x.product.gateway.charge(order_row[1])
    x.external(wait)
    x.db.exe("UPDATE pagamentos SET estado=? WHERE id=?", ("aprovado" if approved else "recusado", payment))
    if not approved:
        raise Recusa("cartão recusado")
    x.db.exe("UPDATE pedidos SET estado='pago' WHERE id=?", (order_row[0],))
    return payment


def route_report(x, r):
    return x.cod["montar_relatorio"](x, x.customer, x.t - r.get("dias", 30) * 1440)


def route_export(x, r):
    return x.cod["exportar_csv"](x, x.customer, x.t - r.get("dias", 30) * 1440)


def route_fiscal_notes(x, r):
    fiscal_notes = x.cod["listar_notas"](x, x.customer)
    x.work(1 + len(fiscal_notes) // 10)
    return len(fiscal_notes)


def route_account(x, r):
    x.cod["atualizar_conta"](x, x.customer, r)
    return True


ROUTE_HANDLERS = {"login": route_login, "catalogo": route_catalog, "busca": route_search, "produto": route_product,
                "carrinho": route_cart, "frete": route_shipping, "pedido": route_order, "pagamento": route_payment,
                "relatorio": route_report, "exportacao": route_export, "notas": route_fiscal_notes, "conta": route_account}

# queue jobs (run in the background process, with the same code as the live version)
def job_fiscal_note(x, ref):
    x.cod["emitir_nota"](x, ref)


def job_email(x, ref):
    x.cod["enviar_email"](x, ref, "confirmação de pedido")


def job_invoice(x, ref):
    c = x.db.fetch_one("SELECT plano FROM clientes WHERE id=?", (ref,))
    value = {"básico": 290.0, "pro": 790.0, "empresarial": 2490.0}[c[0]]
    x.db.exe("INSERT INTO faturas (cliente, mes, valor, estado, t) VALUES (?,?,?,?,?)", (ref, x.month, value, "aberta", x.t))
    x.cod["enviar_email"](x, ref, "fatura do mês")


JOB_HANDLERS = {"nota": job_fiscal_note, "email": job_email, "fatura": job_invoice}


# ======================================================================================================== implementation repository
def _harvest():
    impl = {}
    for name, obj in globals().items():
        if callable(obj) and "__" in name and not name.startswith("_"):
            func_name, variant = name.split("__", 1)
            impl.setdefault(func_name, {})[variant] = obj
    return impl


IMPLEMENTATIONS = _harvest()

INITIAL = {"normalizar_login": "correta", "verificar_senha": "simples", "registrar_dispositivo": "nada",
           "guardar_sessao": "com_expiracao", "atualizar_conta": "correta", "listar_produtos": "pagina_20", "paginar": "correta",
           "recomendar": "nenhuma", "normalizar_termo": "correta", "buscar_produtos": "varredura", "detalhar_produto": "simples",
           "ler_quantidade": "correta", "reservar_estoque": "correta", "verificar_fraude": "nada", "calcular_frete": "correta",
           "cotar_transportadoras": "uma", "autenticar_pagamento": "direto", "registrar_cobranca": "correta",
           "emitir_nota": "correta", "listar_notas": "todas", "montar_relatorio": "filtrado", "exportar_csv": "lote",
           "enviar_email": "correta"}

FUNCTION_COMPONENT = {"normalizar_login": "login", "verificar_senha": "login", "registrar_dispositivo": "login",
                     "guardar_sessao": "login", "atualizar_conta": "login", "listar_produtos": "catalogo", "paginar": "catalogo",
                     "recomendar": "catalogo", "normalizar_termo": "catalogo", "buscar_produtos": "catalogo",
                     "detalhar_produto": "catalogo", "ler_quantidade": "pedido", "reservar_estoque": "pedido",
                     "verificar_fraude": "pedido", "calcular_frete": "frete", "cotar_transportadoras": "frete",
                     "autenticar_pagamento": "pagamento", "registrar_cobranca": "pagamento", "emitir_nota": "fiscal",
                     "listar_notas": "fiscal", "montar_relatorio": "relatorio", "exportar_csv": "relatorio",
                     "enviar_email": "notificacao"}

# defects a commit can bring: (function, defective implementation) -> (how the defect shows up, what it does)
DEFECTS = {
    ("normalizar_login", "ascii"): ("exceção", "o login quebra para quem tem acento no nome de usuário"),
    ("guardar_sessao", "sem_expiracao"): ("memória", "as sessões nunca saem do cache e a memória cresce até o processo cair"),
    ("atualizar_conta", "telefone"): ("exceção", "a conta não salva para cliente sem telefone"),
    ("paginar", "ultima_pagina"): ("exceção", "a última página incompleta do catálogo quebra"),
    ("normalizar_termo", "ascii"): ("exceção", "a busca quebra com termo acentuado"),
    ("ler_quantidade", "um_digito"): ("exceção", "carrinho e pedido quebram com quantidade de dois algarismos ou mais"),
    ("calcular_frete", "numerico"): ("exceção", "frete e pedido quebram para CEP que começa com zero"),
    ("registrar_cobranca", "sem_verificacao"): ("gravação dupla", "o clique duplo cobra e grava o pagamento duas vezes"),
    ("emitir_nota", "aliquota_regional"): ("fila", "a nota falha para clientes fora do Sul e do Sudeste e a fila cresce"),
    ("montar_relatorio", "sem_filtro"): ("lento", "o relatório lê todos os pedidos; fica lento e estoura quando a tabela cresce"),
    ("exportar_csv", "n_mais_um"): ("lento", "a exportação faz uma consulta por pedido"),
    ("enviar_email", "nome_fantasia"): ("fila", "o e-mail falha para cliente sem nome fantasia e a fila cresce"),
}

# roadmap features, in order: (function, new implementation, route that changes, epic title)
FEATURES = (
    ("recomendar", "historico", "catalogo", "recomendações no catálogo"),
    ("verificar_fraude", "antifraude", "pedido", "análise antifraude nos pedidos"),
    ("listar_notas", "paginada", "notas", "notas fiscais paginadas"),
    ("buscar_produtos", "indice", "busca", "índice de busca"),
    ("montar_relatorio", "por_item", "relatorio", "relatório por item"),
    ("verificar_senha", "reforcada", "login", "senha reforçada"),
    ("cotar_transportadoras", "duas", "frete", "cotação em duas transportadoras"),
    ("autenticar_pagamento", "tres_ds", "pagamento", "autenticação do pagador"),
    ("registrar_dispositivo", "grava", "login", "registro de dispositivos"),
    ("detalhar_produto", "relacionados", "produto", "produtos relacionados"),
    ("listar_produtos", "pagina_40", "catalogo", "catálogo com quarenta itens por página"),
    ("exportar_csv", "compactada", "exportacao", "exportação compactada"),
    ("buscar_produtos", "sinonimos", "busca", "busca por sinônimos"),
    ("recomendar", "historico_curto", "catalogo", "recomendações mais leves"),
)

FUNCTION_OF_CODE = {}
for _func_name, _variants in IMPLEMENTATIONS.items():
    for _f in _variants.values():
        FUNCTION_OF_CODE[_f.__code__] = _func_name


def failing_function(tb):
    """Read the exception traceback and return the product function where it was raised (the deepest one)."""
    found = None
    while tb is not None:
        f = FUNCTION_OF_CODE.get(tb.tb_frame.f_code)
        if f is not None:
            found = f
        tb = tb.tb_next
    return found


def feature(idx):
    """Feature number `idx` of the roadmap. When the roadmap ends it starts over as a revision: each function goes back to the
    implementation it had before that feature, and on the following pass it moves forward again. The code keeps changing the same
    way in long runs."""
    n = len(FEATURES)
    func_name, variant, route, title = FEATURES[idx % n]
    if (idx // n) % 2 == 1:
        variant = INITIAL[func_name]
        for f in FEATURES[:idx % n]:
            if f[0] == func_name:
                variant = f[1]
        title = "revisão de " + title
    return func_name, variant, route, title


# ======================================================================================================== quality's tests
TESTS = {}


def _test(func_name, name, kind="funcional"):
    def register(f):
        TESTS.setdefault(func_name, []).append((name, f, kind))
        return f
    return register


@_test("normalizar_login", "login simples")
def _t(e): e.route("login", {"login": "maria.ensaio"})
@_test("normalizar_login", "login com acento")
def _t(e): e.route("login", {"login": "joão.ensaio"})
@_test("verificar_senha", "senha confere")
def _t(e): e.route("login", {"login": "maria.ensaio"})
@_test("registrar_dispositivo", "dispositivo novo")
def _t(e): e.route("login", {"login": "maria.ensaio"})
@_test("guardar_sessao", "sessões expiram")
def _t(e):
    cache = {}
    f = e.cod["guardar_sessao"]
    f(cache, "a", 1, 0)
    f(cache, "b", 2, 10)
    f(cache, "c", 3, 400)
    assert len(cache) == 1, "sessões antigas continuam no cache"
@_test("atualizar_conta", "conta com telefone")
def _t(e): e.route("conta", {"telefone": "31 3333-0000", "nome_fantasia": "Loja Ensaio"}, customer=1)
@_test("atualizar_conta", "conta sem telefone")
def _t(e): e.route("conta", {"telefone": None, "nome_fantasia": "Loja Ensaio"}, customer=2)
@_test("listar_produtos", "lista a categoria")
def _t(e): assert e.route("catalogo", {"categoria": "mercearia", "pagina": 1}) > 0
@_test("paginar", "primeira página")
def _t(e): e.route("catalogo", {"categoria": "mercearia", "pagina": 1})
@_test("paginar", "última página incompleta")
def _t(e):
    for page in range(1, 5):
        e.route("catalogo", {"categoria": "mercearia", "pagina": page})
@_test("recomendar", "catálogo com recomendação")
def _t(e): e.route("catalogo", {"categoria": "limpeza", "pagina": 1}, customer=1)
@_test("normalizar_termo", "termo simples")
def _t(e): e.route("busca", {"termo": "arroz"})
@_test("normalizar_termo", "termo com acento")
def _t(e): e.route("busca", {"termo": "açúcar"})
@_test("buscar_produtos", "busca acha o produto")
def _t(e): assert e.route("busca", {"termo": "arroz"}) > 0
@_test("detalhar_produto", "detalhe do produto")
def _t(e): e.route("produto", {"produto": 3})
@_test("ler_quantidade", "quantidade unitária")
def _t(e): e.route("carrinho", {"produto": 3, "quantidade": "1"})
@_test("ler_quantidade", "quantidade de caixa")
def _t(e): e.route("carrinho", {"produto": 3, "quantidade": "12"})
@_test("reservar_estoque", "pedido reserva estoque")
def _t(e): e.route("pedido", {"itens": [(3, "2")], "cep": "30140-071"})
@_test("verificar_fraude", "pedido passa pela análise")
def _t(e): e.route("pedido", {"itens": [(4, "1")], "cep": "30140-071"})
@_test("calcular_frete", "frete para Minas")
def _t(e): e.route("frete", {"cep": "30140-071"})
@_test("calcular_frete", "frete para São Paulo")
def _t(e): e.route("frete", {"cep": "01310-100"})
@_test("cotar_transportadoras", "cotação de frete")
def _t(e): assert e.route("frete", {"cep": "80010-000"}) > 0
@_test("autenticar_pagamento", "pagamento autenticado")
def _t(e):
    pid, _ = e.route("pedido", {"itens": [(5, "1")], "cep": "30140-071"})
    e.route("pagamento", {"pedido": pid})
@_test("registrar_cobranca", "pagamento simples")
def _t(e):
    pid, _ = e.route("pedido", {"itens": [(6, "1")], "cep": "30140-071"})
    e.route("pagamento", {"pedido": pid})
@_test("registrar_cobranca", "clique duplo no pagamento")
def _t(e):
    pid, _ = e.route("pedido", {"itens": [(7, "1")], "cep": "30140-071"})
    e.route("pagamento", {"pedido": pid})
    try:
        e.route("pagamento", {"pedido": pid})
    except Recusa:
        pass
    n = e.db.fetch_one("SELECT COUNT(*) FROM pagamentos WHERE pedido=? AND estado='aprovado'", (pid,))[0]
    assert n == 1, "pagamento gravado duas vezes"
@_test("emitir_nota", "nota de Minas")
def _t(e):
    pid, _ = e.route("pedido", {"itens": [(8, "1")], "cep": "30140-071"}, customer=1)
    e.work("nota", pid)
@_test("emitir_nota", "nota da Bahia")
def _t(e):
    pid, _ = e.route("pedido", {"itens": [(8, "1")], "cep": "40020-000"}, customer=3)
    e.work("nota", pid)
@_test("listar_notas", "lista as notas")
def _t(e): e.route("notas", {}, customer=1)
@_test("montar_relatorio", "relatório do mês")
def _t(e): e.route("relatorio", {}, customer=1)
@_test("montar_relatorio", "desempenho do relatório", "desempenho")
def _t(e): e.performance("relatorio", {}, max_instructions=6000, max_queries=10)
@_test("exportar_csv", "exportação do mês")
def _t(e): e.route("exportacao", {}, customer=1)
@_test("exportar_csv", "desempenho da exportação", "desempenho")
def _t(e): e.performance("exportacao", {}, max_instructions=6000, max_queries=10)
@_test("enviar_email", "e-mail com nome fantasia")
def _t(e): e.work("email", 1)
@_test("enviar_email", "e-mail sem nome fantasia")
def _t(e): e.work("email", 4)


def component_tests(component):
    """The tests of every function of a component, in code order."""
    return [(func_name, name, f, kind) for func_name, entries in TESTS.items() if FUNCTION_COMPONENT[func_name] == component
            for name, f, kind in entries]
