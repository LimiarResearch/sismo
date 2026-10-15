"""The company's live software: a service with routes, a real database (in-memory SQLite), a background job queue, scheduled jobs
and the disk volume the database lives on. The routes are called by the customers (customers.py), by the operations availability
probe (one test call per route every minute) and by quality, in a separate test environment.

What runs is the code of the live version (codebase.py). Metrics come from what the code did: each request counts the queries and
the instructions the database executed (the database reports every ten instructions), the application work and the wait for
external services (payment gateway, carriers, anti-fraud); latency is a function of that and of the CPU load. CPU and memory are a
function of what the requests and jobs did and of what the process holds (the session cache, the queue). The database size is the
number of pages SQLite occupies; when the volume fills up, every write fails with SQLite's own error, and the product goes down.

External services are the outside world: their response times and refusals are random."""
import collections
import sqlite3

from . import codebase
from .codebase import Recusa
from .catalog import ROUTES, DIGIT_REGION, rng_for, MINUTES_PER_DAY

PAGE_BYTES = 4096
ROUTE_BASE_MS = {"login": 38.0, "catalogo": 30.0, "busca": 42.0, "produto": 22.0, "carrinho": 26.0, "frete": 18.0, "pedido": 55.0,
                "pagamento": 40.0, "relatorio": 95.0, "exportacao": 120.0, "notas": 28.0, "conta": 30.0}
MS_PER_QUERY = 1.1          # round trip to the database
MS_PER_INSTRUCTIONS = 0.02       # per ten database instructions
MS_PER_WORK = 0.1          # per unit of application work
MEMORY_LIMIT_MB = 2048.0
QUEUE_CAPACITY = 40       # jobs per minute


class Database:
    """The product's connection to its database, counting what it does."""

    def __init__(self, con):
        self.instr = 0
        self.queries = 0
        self.writes = 0
        self.connect(con)

    def connect(self, con):
        self.con = con
        con.set_progress_handler(self._tick, 10)

    def _tick(self):
        self.instr += 1
        return 0

    def fetch_one(self, sql, a=()):
        self.queries += 1
        return self.con.execute(sql, a).fetchone()

    def fetch_all(self, sql, a=()):
        self.queries += 1
        return self.con.execute(sql, a).fetchall()

    def cursor(self, sql, a=()):
        self.queries += 1
        return self.con.execute(sql, a)

    def exe(self, sql, a=()):
        self.writes += 1
        return self.con.execute(sql, a)

    def __getstate__(self):
        d = dict(self.__dict__)
        d["con"] = None
        return d


class Execution:
    """The context of a request or a job: who asks, with which code, how much work and how much waiting."""
    __slots__ = ("db", "cod", "product", "t", "customer", "user", "simulated", "month", "work_units", "ext")

    def work(self, n):
        self.work_units += n

    def external(self, ms):
        self.ext += ms


# ---------------------------------------------------------------------------------------------------- the outside world
class Gateway:
    def __init__(self, rng):
        self.s = rng

    def charge(self, value):
        wait = self.s.lognormvariate(5.75, 0.35)            # about 300 ms
        return self.s.random() > 0.04, wait

    def authenticate(self):
        return self.s.lognormvariate(5.3, 0.4)

    def lookup(self):
        return self.s.lognormvariate(4.3, 0.3)


class Carriers:
    def __init__(self, rng):
        self.s = rng
        self.failures = 0

    def quote(self):
        if self.s.random() < 0.0015:
            self.failures += 1
            raise ConnectionError("transportadora não respondeu")
        return self.s.lognormvariate(5.1, 0.35)


class AntiFraud:
    def __init__(self, rng):
        self.s = rng

    def lookup(self):
        return self.s.lognormvariate(4.9, 0.3)


class _OutsideStub:
    """External services in the test environment: they always approve, with a fixed wait."""
    failures = 0

    def charge(self, value): return True, 300.0
    def authenticate(self): return 200.0
    def lookup(self): return 80.0
    def quote(self): return 160.0


# ---------------------------------------------------------------------------------------------------- schema and seed data
SCHEMA = """
CREATE TABLE clientes (id INTEGER PRIMARY KEY, nome_fantasia TEXT, razao TEXT, plano TEXT, cep TEXT, uf TEXT, regiao INTEGER,
    telefone TEXT, criado_em INTEGER, ativo INTEGER);
CREATE TABLE usuarios (id INTEGER PRIMARY KEY, cliente INTEGER, login TEXT, ativo INTEGER);
CREATE UNIQUE INDEX u_login ON usuarios(login);
CREATE TABLE sessoes (token TEXT PRIMARY KEY, usuario INTEGER, criada_em INTEGER);
CREATE INDEX s_t ON sessoes(criada_em);
CREATE TABLE dispositivos (id INTEGER PRIMARY KEY, usuario INTEGER, t INTEGER);
CREATE INDEX d_u ON dispositivos(usuario);
CREATE TABLE produtos (id INTEGER PRIMARY KEY, nome TEXT, nome_busca TEXT, categoria TEXT, preco REAL, estoque INTEGER,
    estoque_alvo INTEGER, peso REAL, vendidos INTEGER);
CREATE INDEX p_cat ON produtos(categoria, nome);
CREATE TABLE palavras (palavra TEXT, produto INTEGER);
CREATE INDEX w_p ON palavras(palavra);
CREATE TABLE carrinhos (id INTEGER PRIMARY KEY, usuario INTEGER, produto INTEGER, quantidade INTEGER, t INTEGER);
CREATE INDEX c_u ON carrinhos(usuario);
CREATE TABLE pedidos (id INTEGER PRIMARY KEY, cliente INTEGER, usuario INTEGER, valor REAL, itens INTEGER, estado TEXT, cep TEXT, t INTEGER);
CREATE INDEX pe_c ON pedidos(cliente, t);
CREATE INDEX pe_t ON pedidos(t);
CREATE TABLE itens_pedido (pedido INTEGER, produto INTEGER, quantidade INTEGER, preco REAL);
CREATE INDEX ip_p ON itens_pedido(pedido);
CREATE TABLE pagamentos (id INTEGER PRIMARY KEY, pedido INTEGER, valor REAL, estado TEXT, t INTEGER);
CREATE INDEX pg_p ON pagamentos(pedido);
CREATE TABLE notas (id INTEGER PRIMARY KEY, pedido INTEGER, cliente INTEGER, uf TEXT, valor REAL, imposto REAL, estado TEXT, t INTEGER);
CREATE INDEX n_c ON notas(cliente, t);
CREATE TABLE emails (id INTEGER PRIMARY KEY, cliente INTEGER, tipo TEXT, assunto TEXT, t INTEGER);
CREATE TABLE faturas (id INTEGER PRIMARY KEY, cliente INTEGER, mes INTEGER, valor REAL, estado TEXT, t INTEGER);
CREATE INDEX f_c ON faturas(cliente, estado);
CREATE TABLE trabalhos (id INTEGER PRIMARY KEY, tipo TEXT, ref INTEGER, estado TEXT, tentativas INTEGER, proxima_em INTEGER, criado_em INTEGER);
CREATE INDEX tr_e ON trabalhos(estado, proxima_em);
CREATE TABLE auditoria (id INTEGER PRIMARY KEY, t INTEGER, rota TEXT, usuario INTEGER);
"""

CATEGORIES = {
    "mercearia": (["arroz", "feijão", "açúcar", "café", "macarrão", "farinha de trigo", "óleo de soja", "sal refinado", "fubá",
                   "aveia", "lentilha", "grão-de-bico", "tapioca", "molho de tomate", "milho"], ["1kg", "5kg", "500g", "tipo 1", "integral"]),
    "bebidas": (["refrigerante", "suco de laranja", "água mineral", "guaraná", "chá mate", "água de coco", "cerveja"], ["350ml", "2l", "1l", "lata", "caixa"]),
    "limpeza": (["detergente", "sabão em pó", "água sanitária", "desinfetante", "esponja", "álcool", "limpa-vidros", "sabão em barra"], ["500ml", "1l", "5l", "pacote", "neutro"]),
    "higiene": (["sabonete", "xampu", "creme dental", "papel higiênico", "desodorante", "condicionador", "fio dental"], ["90g", "300ml", "pacote", "família", "sem perfume"]),
    "padaria": (["pão de forma", "pão de queijo", "bolacha", "biscoito", "torrada", "bolo"], ["integral", "tradicional", "500g", "pacote"]),
    "frios": (["queijo muçarela", "presunto", "requeijão", "manteiga", "iogurte", "margarina"], ["200g", "500g", "fatiado", "pote"]),
    "hortifrúti": (["batata", "cebola", "tomate", "maçã", "banana", "limão", "mamão", "alho"], ["kg", "bandeja", "orgânico"]),
    "papelaria": (["caderno", "caneta", "lápis", "papel sulfite", "envelope", "grampeador", "pasta"], ["unidade", "caixa", "pacote", "A4"]),
    "utilidades": (["copo", "prato", "talher", "panela", "pote", "garrafa térmica", "lixeira"], ["plástico", "vidro", "inox", "grande", "pequeno"]),
    "pet": (["ração", "areia higiênica", "petisco", "coleira"], ["cão", "gato", "1kg", "10kg", "filhote"]),
    "congelados": (["pizza", "lasanha", "hambúrguer", "batata palito", "pão de alho", "sorvete"], ["congelado", "família", "500g", "1kg"]),
    "descartáveis": (["guardanapo", "copo descartável", "sacola", "papel toalha", "luva", "touca"], ["pacote", "caixa", "100 unidades", "50 unidades"]),
}


def _strip_accents(text):
    return codebase.normalizar_termo__correta(text)


def generate_products(rng):
    products = []
    for category, (bases, variants) in CATEGORIES.items():
        target = rng.randint(26, 74)
        names = []
        for base in bases:
            for v in variants:
                names.append(f"{base} {v}")
        rng.shuffle(names)
        for name in sorted(names[:target]):
            price = round(rng.uniform(2.0, 90.0), 2)
            stock = rng.randint(300, 2500)
            products.append((name, _strip_accents(name), category, price, stock, stock, round(rng.uniform(0.1, 6.0), 2)))
    return products


def create_db(products, customers, users):
    con = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False, cached_statements=0)
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO produtos (nome, nome_busca, categoria, preco, estoque, estoque_alvo, peso, vendidos) "
                    "VALUES (?,?,?,?,?,?,?,0)", products)
    for pid, search_name in con.execute("SELECT id, nome_busca FROM produtos").fetchall():
        for word in search_name.split():
            if len(word) > 2:
                con.execute("INSERT INTO palavras (palavra, produto) VALUES (?,?)", (word, pid))
    con.executemany("INSERT INTO clientes (id, nome_fantasia, razao, plano, cep, uf, regiao, telefone, criado_em, ativo) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)", customers)
    con.executemany("INSERT INTO usuarios (id, cliente, login, ativo) VALUES (?,?,?,1)", users)
    return con


# ---------------------------------------------------------------------------------------------------- the service
class Product:
    def __init__(self, seed, customers, users, est_pages_per_day, headroom_days):
        rng = rng_for(seed, "catalogo de produtos")
        self.net_rng = rng_for(seed, "rede")
        outside = rng_for(seed, "servicos de fora")
        self.gateway, self.carriers, self.antifraud = Gateway(outside), Carriers(outside), AntiFraud(outside)
        self.initial_products = generate_products(rng)
        con = create_db(self.initial_products, [(0, "Monitoramento", "Conta de monitoramento", "empresarial", "30140-071", "MG", 2,
                                                    "31 3000-0000", 0, 1)] + customers,
                          [(0, 0, "monitoramento")] + users)
        con.execute("INSERT INTO pedidos (id, cliente, usuario, valor, itens, estado, cep, t) VALUES (1, 0, 0, 10.0, 1, 'criado', '30140-071', 0)")
        con.executemany("INSERT INTO notas (pedido, cliente, uf, valor, imposto, estado, t) VALUES (1, 0, 'MG', 10.0, 1.8, 'emitida', ?)",
                        [(-i * 97,) for i in range(1, 181)])
        self.db = Database(con)
        self.categories = list(CATEGORIES)
        self.code_map = dict(codebase.INITIAL)
        self._resolve()
        self.version = "1.0"
        self.session_cache = {}
        self.tokens = 0
        self.restarting_until = 0                    # while t < restarting_until the process is restarting
        self.restarts_min = 0
        self.errors = collections.deque(maxlen=4000)        # (t, route, function, exception type)
        self.slow_requests = collections.deque(maxlen=2000)       # (t, route, deepest function, instructions)
        self.queue_pending = 0
        self.queue_done = self.queue_failures = self.emails_ok = self.emails_failed = self.fiscal_ok = self.fiscal_failed = 0
        self.invoices_issued = 0
        self.first_audit_of_day = []               # (t, id): to delete old audit rows without scanning the table
        self.cron_work_ms = 0.0
        self.cron_running = 0
        self.cron_rows = 0
        self.restocked = 0
        self.rho = 0.05
        self.memory = 400.0
        self.daily_pages = collections.deque(maxlen=15)   # (day, pages in use) so operations can estimate growth
        used = self.pages_in_use()
        self.volume_pages = int(used + est_pages_per_day * headroom_days)
        self._apply_volume()
        self._reset_minute()
        self.probe_fail_streak = 0
        self.window = collections.deque(maxlen=30)          # the last minutes, for monitoring
        self.latency_history = {r: collections.deque(maxlen=7 * 24) for r in ROUTES}   # hourly means, for alerts
        self._hourly_lat = {r: [0.0, 0] for r in ROUTES}

    # ---------- live code ----------
    def _resolve(self):
        self.cod = {f: codebase.IMPLEMENTATIONS[f][v] for f, v in self.code_map.items()}

    def deploy(self, t, new_code, version):
        """Swap the live code. The process restarts (the session cache is lost) without dropping requests."""
        self.code_map = dict(new_code)
        self._resolve()
        self.version = version
        self.session_cache = {}
        self.restarts_min += 1
        self._x.cod = self.cod

    def new_token(self):
        self.tokens += 1
        return f"s{self.tokens:09d}"

    # ---------- disk ----------
    def pages_in_use(self):
        c = self.db.con
        return c.execute("PRAGMA page_count").fetchone()[0] - c.execute("PRAGMA freelist_count").fetchone()[0]

    def _apply_volume(self):
        current = self.db.con.execute("PRAGMA page_count").fetchone()[0]
        self.db.con.execute(f"PRAGMA max_page_count = {max(self.volume_pages, current)}")

    def grow_volume(self, pages):
        self.volume_pages = int(pages)
        self._apply_volume()

    def purge_old_audit(self, t, days):
        """Delete audit rows older than `days` days; return how many rows were removed."""
        limit = None
        for tt, ident in self.first_audit_of_day:
            if tt <= t - days * MINUTES_PER_DAY:
                limit = ident
        if limit is None:
            return 0
        n = self.db.con.execute("DELETE FROM auditoria WHERE id < ?", (limit,)).rowcount
        self.first_audit_of_day = [(tt, i) for tt, i in self.first_audit_of_day if i >= limit]
        return n

    # ---------- one request ----------
    def call(self, t, route, req, customer, user, simulated=False):
        """One request to a route. Returns (state, latency in ms, failing function) with state "ok", "erro" or "recusa"."""
        m = self.m
        i = self._route_idx[route]
        m_req, m_err, m_refused, m_lat, m_lats, m_distinct = m["req"], m["erro"], m["recusa"], m["lat"], m["lats"][i], m["cli"][i]
        m_req[i] += 1
        if customer:
            m_distinct.add(customer)
        if t < self.restarting_until:                               # the process is restarting: the load balancer returns an error right away
            m_err[i] += 1
            m_lat[i] += 4.0
            m_lats.append(4.0)
            return "erro", 4.0, None
        db = self.db
        i0, c0, e0 = db.instr, db.queries, db.writes
        x = self._x
        x.t, x.customer, x.user, x.simulated, x.work_units, x.ext = t, customer, user, simulated, 0, 0.0
        state, failed_fn = "ok", None
        try:
            db.exe("INSERT INTO auditoria (t, rota, usuario) VALUES (?,?,?)", (t, route, user))
            codebase.ROUTE_HANDLERS[route](x, req)
        except Recusa:
            state = "recusa"
        except Exception as e:
            state = "erro"
            failed_fn = codebase.failing_function(e.__traceback__)
            self.errors.append((t, route, failed_fn, type(e).__name__))
        instr = db.instr - i0
        service_ms = ROUTE_BASE_MS[route] + MS_PER_QUERY * ((db.queries - c0) + (db.writes - e0)) + MS_PER_INSTRUCTIONS * instr + MS_PER_WORK * x.work_units
        if state == "erro":
            service_ms += 15.0
        lat = (service_ms * (1.0 + 2.5 * self.rho * self.rho) + x.ext) * self.net_rng.lognormvariate(0.0, 0.12)
        self.cpu_ms += service_ms * 4.0
        if instr > 2000:
            self.slow_requests.append((t, route, None, instr))
        if state == "erro":
            m_err[i] += 1
        elif state == "recusa":
            m_refused[i] += 1
        m_lat[i] += lat
        m_lats.append(lat)
        if not simulated:
            if route == "frete" or route == "pedido":
                reg = DIGIT_REGION.get(req["cep"][:1], 0)
                if route == "frete":
                    m["frete_reg"][reg] += 1
                    if state == "erro":
                        m["frete_reg_erro"][reg] += 1
            if state == "ok":
                if route == "pagamento":
                    m["pag_ok"] += 1
                    m["pag_pedidos"].add(req["pedido"])
                elif route == "pedido":
                    m["carrinho_fechado"] += 1
            elif state == "recusa" and route == "pagamento":
                m["pag_recusa"] += 1
        return state, lat, failed_fn

    # ---------- job queue ----------
    def enqueue(self, kind, ref, t):
        self.db.exe("INSERT INTO trabalhos (tipo, ref, estado, tentativas, proxima_em, criado_em) VALUES (?,?,?,?,?,?)",
                    (kind, ref, "pendente", 0, t, t))
        self.queue_pending += 1

    def process_queue(self, t, month):
        if t < self.restarting_until:
            return
        db = self.db
        try:
            batch = db.fetch_all("SELECT id, tipo, ref, tentativas FROM trabalhos WHERE estado='pendente' AND proxima_em<=? ORDER BY proxima_em, id LIMIT ?",
                            (t, QUEUE_CAPACITY))
        except sqlite3.Error:
            return
        x = self._x
        for ident, kind, ref, attempts in batch:
            i0, c0, e0 = db.instr, db.queries, db.writes
            x.t, x.customer, x.user, x.simulated, x.work_units, x.ext, x.month = t, 0, 0, False, 0, 0.0, month
            try:
                codebase.JOB_HANDLERS[kind](x, ref)
                db.exe("DELETE FROM trabalhos WHERE id=?", (ident,))
                self.queue_pending -= 1
                self.queue_done += 1
                if kind == "nota":
                    self.fiscal_ok += 1
                elif kind == "fatura":
                    self.invoices_issued += 1
                    self.emails_ok += 1
                else:
                    self.emails_ok += 1
            except Exception as e:
                self.queue_failures += 1
                failed_fn = codebase.failing_function(e.__traceback__)
                self.errors.append((t, "fila", failed_fn, type(e).__name__))
                if kind == "nota":
                    self.fiscal_failed += 1
                else:
                    self.emails_failed += 1
                try:
                    if attempts + 1 >= 12:
                        db.exe("UPDATE trabalhos SET estado='falha', tentativas=? WHERE id=?", (attempts + 1, ident))
                        self.queue_pending -= 1
                    else:
                        db.exe("UPDATE trabalhos SET tentativas=?, proxima_em=? WHERE id=?",
                               (attempts + 1, t + min(720, 5 * 2 ** attempts), ident))
                except sqlite3.Error:
                    pass
            self.cpu_ms += 4.0 * (8.0 + MS_PER_QUERY * ((db.queries - c0) + (db.writes - e0)) + MS_PER_INSTRUCTIONS * (db.instr - i0) + MS_PER_WORK * x.work_units)

    # ---------- the server's scheduled jobs (by the calendar) ----------
    def run_scheduled_jobs(self, t, cal):
        m = cal.minute
        db = self.db.con
        self.cron_running = 0
        try:
            if 120 <= m < 136:                               # nightly backup: reads the whole database
                self.cron_running += 1
                pages = db.execute("PRAGMA page_count").fetchone()[0]
                self.cron_work_ms += pages * 0.35
                self.cron_rows += pages // 16
            if m == 180:                                     # cleanup of old sessions and carts
                self.cron_running += 1
                n = db.execute("DELETE FROM sessoes WHERE criada_em < ?", (t - 2 * MINUTES_PER_DAY,)).rowcount
                n += db.execute("DELETE FROM carrinhos WHERE t < ?", (t - 2 * MINUTES_PER_DAY,)).rowcount
                self.cron_rows += n
                self.cron_work_ms += 200.0 + n * 0.05
            if m == 240:                                     # suppliers restock
                self.cron_running += 1
                missing = db.execute("SELECT COALESCE(SUM(estoque_alvo - estoque), 0) FROM produtos WHERE estoque < estoque_alvo / 2").fetchone()[0]
                db.execute("UPDATE produtos SET estoque = estoque_alvo WHERE estoque < estoque_alvo / 2")
                self.restocked += missing
                self.cron_work_ms += 300.0
            if m == 270 and cal.weekday == 6:             # weekly index rebuild
                self.cron_running += 1
                db.execute("REINDEX pe_c")
                db.execute("REINDEX ip_p")
                self.cron_work_ms += 9000.0
            if m == 420:                                     # summary of the previous day
                self.cron_running += 1
                r = db.execute("SELECT COUNT(*), COALESCE(SUM(valor), 0) FROM pedidos WHERE t >= ?", (t - MINUTES_PER_DAY,)).fetchone()
                self.cron_rows += r[0]
                self.cron_work_ms += 400.0 + r[0] * 0.3
            if m == 360 and cal.day_of_month == 1:                 # monthly billing
                self.cron_running += 1
                for (cid,) in db.execute("SELECT id FROM clientes WHERE ativo=1 AND id>0 ORDER BY id").fetchall():
                    self.enqueue("fatura", cid, t)
                self.cron_work_ms += 2000.0
        except sqlite3.Error:
            pass

    # ---------- operations probe ----------
    PROBE_REQUESTS = {"login": {"login": "monitoramento"}, "catalogo": {"categoria": "mercearia", "pagina": 1}, "busca": {"termo": "arroz"},
             "produto": {"produto": 1}, "carrinho": {"produto": 1, "quantidade": "1"}, "frete": {"cep": "30140-071"},
             "pedido": {"itens": [(1, "1")], "cep": "30140-071"}, "pagamento": {"pedido": 1}, "relatorio": {}, "exportacao": {},
             "notas": {}, "conta": {"telefone": "31 3000-0000", "nome_fantasia": "Monitoramento"}}

    def run_probe(self, t):
        failures = 0
        for route in ROUTES:
            state, _, _ = self.call(t, route, self.PROBE_REQUESTS[route], 0, 0, simulated=True)
            if state == "erro":
                failures += 1
        self.m["sonda"] = len(ROUTES)
        self.m["sonda_falhas"] = failures
        self.probe_fail_streak = self.probe_fail_streak + 1 if failures >= len(ROUTES) // 2 else 0

    # ---------- end of the minute ----------
    def _reset_minute(self):
        n = len(ROUTES)
        self._route_idx = {r: i for i, r in enumerate(ROUTES)}
        self._x = Execution()
        self._x.db, self._x.cod, self._x.product, self._x.month = self.db, self.cod, self, 0
        self.m = {"req": [0] * n, "erro": [0] * n, "recusa": [0] * n, "lat": [0.0] * n, "lats": [[] for _ in range(n)],
                  "cli": [set() for _ in range(n)], "frete_reg": [0] * 6, "frete_reg_erro": [0] * 6, "pag_ok": 0, "pag_recusa": 0,
                  "pag_pedidos": set(), "carrinho_fechado": 0, "sonda": 0, "sonda_falhas": 0}
        self.cpu_ms = 0.0
        self.db.instr = self.db.queries = self.db.writes = 0

    def close_minute(self, t, cal):
        """Close the minute's tallies: per-route metrics, CPU, memory, disk, queue."""
        m = self.m
        db = self.db
        routes = {}
        for i, r in enumerate(ROUTES):
            n = m["req"][i]
            lats = m["lats"][i]
            if lats:
                lats.sort()
                p95 = lats[min(len(lats) - 1, int(0.95 * len(lats)))]
                avg = m["lat"][i] / n
            else:
                p95 = avg = 0.0
            distinct = m["cli"][i]
            routes[r] = (n, m["erro"][i], m["recusa"][i], avg, p95, len(distinct))
            acc = self._hourly_lat[r]
            acc[0] += avg
            acc[1] += 1
        if cal.minute % 60 == 59:
            for r in ROUTES:
                acc = self._hourly_lat[r]
                if acc[1]:
                    self.latency_history[r].append(acc[0] / acc[1])
                self._hourly_lat[r] = [0.0, 0]
        cpu_ms = self.cpu_ms + self.cron_work_ms
        self.cron_work_ms = 0.0
        cpu = min(100.0, cpu_ms / 600.0 + 2.0)
        self.rho = cpu / 100.0
        # process memory: what it holds right now
        self.memory = 410.0 + 0.30 * len(self.session_cache) + 0.004 * self.queue_pending + 0.004 * len(self.errors) + 0.0004 * db.instr
        restarts = self.restarts_min
        if self.memory > MEMORY_LIMIT_MB and t >= self.restarting_until:
            self.restarting_until = t + 2                       # the system kills the process and the supervisor brings it back up
            self.session_cache = {}
            restarts += 1
            self.errors.append((t, "processo", "guardar_sessao", "MemoryError"))
        con = db.con
        pages = con.execute("PRAGMA page_count").fetchone()[0]
        free_pages = con.execute("PRAGMA freelist_count").fetchone()[0]
        used_pages = pages - free_pages
        if cal.minute == 0:
            r = con.execute("SELECT MAX(id) FROM auditoria").fetchone()[0]
            if r is not None:
                self.first_audit_of_day.append((t, r))
            self.daily_pages.append((t, used_pages))
        try:
            oldest_queued = con.execute("SELECT MIN(criado_em) FROM trabalhos WHERE estado='pendente'").fetchone()[0]
            out_of_stock = con.execute("SELECT COUNT(*) FROM produtos WHERE estoque < 1").fetchone()[0]
            orders = con.execute("SELECT COUNT(*), COALESCE(SUM(valor), 0), COALESCE(SUM(itens), 0) FROM pedidos WHERE t=?", (t,)).fetchone()
            orders_by_region = con.execute("SELECT c.regiao, COUNT(*) FROM pedidos p JOIN clientes c ON c.id = p.cliente WHERE p.t=? GROUP BY c.regiao", (t,)).fetchall()
            orders_by_plan = con.execute("SELECT c.plano, COUNT(*) FROM pedidos p JOIN clientes c ON c.id = p.cliente WHERE p.t=? GROUP BY c.plano", (t,)).fetchall()
        except sqlite3.Error:
            oldest_queued, out_of_stock, orders, orders_by_region, orders_by_plan = None, 0, (0, 0.0, 0), [], []
        output = {
            "rotas": routes,
            "cpu": cpu,
            "memoria": self.memory,
            "reinicios": restarts,
            "paginas": used_pages,
            "livre_paginas": self.volume_pages - pages + free_pages,
            "consultas": db.queries,
            "escritas": db.writes,
            "instrucoes": db.instr,
            "fila": (self.queue_pending, self.queue_done, self.queue_failures,
                     (t - oldest_queued) if oldest_queued is not None else 0),
            "emails": (self.emails_ok, self.emails_failed),
            "notas": (self.fiscal_ok, self.fiscal_failed),
            "faturas_emitidas": self.invoices_issued,
            "gateway": (m["req"][self._route_idx["pagamento"]], m["pag_recusa"]),
            "frete_reg": (m["frete_reg"], m["frete_reg_erro"]),
            "sonda": (m["sonda"], m["sonda_falhas"]),
            "cron": (self.cron_running, self.cron_rows),
            "repostas": self.restocked,
            "sem_estoque": out_of_stock,
            "pedidos": orders,
            "pedidos_reg": orders_by_region,
            "pedidos_plano": orders_by_plan,
            "pag": (m["pag_ok"], len(m["pag_pedidos"]), m["pag_recusa"]),
            "lentas": sum(1 for x in self.slow_requests if x[0] == t),
        }
        self.window.append((t, routes, m["sonda_falhas"]))
        self.restarts_min = 0
        self.queue_done = self.queue_failures = self.emails_ok = self.emails_failed = self.fiscal_ok = self.fiscal_failed = 0
        self.invoices_issued = 0
        self.cron_rows = 0
        self.restocked = 0
        self._reset_minute()
        return output

    # ---------- what monitoring reads ----------
    def errors_in_window(self, route, minutes):
        req = err = 0
        i = self._route_idx[route]
        for item in list(self.window)[-minutes:]:
            v = item[1][route]
            req += v[0]
            err += v[1]
        return req, err

    def latency_in_window(self, route, minutes):
        vals = [item[1][route][3] for item in list(self.window)[-minutes:]]
        return sum(vals) / len(vals) if vals else 0.0

    def usual_latency(self, route):
        h = self.latency_history[route]
        if len(h) < 24:
            return None
        v = sorted(h)
        return v[len(v) // 2]

    def connect(self, con):
        con.execute("SELECT name FROM sqlite_master").fetchall()     # read the schema before the instruction counter is attached
        self.db.connect(con)
        self._apply_volume()
        self._x = Execution()
        self._x.db, self._x.cod, self._x.product, self._x.month = self.db, self.cod, self, 0

    def __getstate__(self):
        d = dict(self.__dict__)
        d["cod"] = None
        d["_x"] = None
        return d

    def __setstate__(self, d):
        self.__dict__.update(d)
        self._resolve()


# ---------------------------------------------------------------------------------------------------- quality's test environment
class TestBed:
    """A small database with known data, to run the tests against a candidate code map."""
    _perf_db_cache = None

    def __init__(self, candidate_code):
        self.cod = {f: codebase.IMPLEMENTATIONS[f][v] for f, v in candidate_code.items()}
        products = []
        for i in range(45):
            name = ["arroz", "feijão", "açúcar", "café", "farinha"][i % 5] + f" ensaio {i:02d}"
            products.append((name, _strip_accents(name), "mercearia", 10.0 + i, 500, 500, 1.0))
        for i in range(12):
            name = ["detergente", "sabão em pó", "esponja"][i % 3] + f" ensaio {i:02d}"
            products.append((name, _strip_accents(name), "limpeza", 5.0 + i, 500, 500, 0.5))
        customers = [(1, "Loja Ensaio", "Loja Ensaio Ltda", "pro", "30140-071", "MG", 2, "31 3333-0000", 0, 1),
                    (2, "Mercado Ensaio", "Mercado Ensaio Ltda", "básico", "80010-000", "PR", 5, None, 0, 1),
                    (3, "Empório Ensaio", "Empório Ensaio Ltda", "pro", "40020-000", "BA", 3, "71 3333-0000", 0, 1),
                    (4, None, "Comércio Ensaio Ltda", "básico", "01310-100", "SP", 0, "11 3333-0000", 0, 1)]
        users = [(1, 1, "maria.ensaio"), (2, 1, "joão.ensaio"), (3, 2, "ana.ensaio"), (4, 3, "pedro.ensaio"), (5, 4, "luís.ensaio")]
        self.con = create_db(products, customers, users)
        self.db = Database(self.con)
        self._prep()

    def _prep(self):
        x = Execution()
        x.db, x.cod, x.product, x.month = self.db, self.cod, self, 0
        self.x = x
        self.gateway = self.carriers = self.antifraud = _OutsideStub()
        self.session_cache = {}
        self.tokens = 0

    def new_token(self):
        self.tokens += 1
        return f"e{self.tokens}"

    def enqueue(self, kind, ref, t):
        return None

    def route(self, route, req, customer=1, user=1):
        x = self.x
        x.t, x.customer, x.user, x.simulated, x.work_units, x.ext = 5000, customer, user, False, 0, 0.0
        return codebase.ROUTE_HANDLERS[route](x, req)

    def work(self, kind, ref):
        x = self.x
        x.t, x.customer, x.user, x.simulated, x.work_units, x.ext = 5000, 0, 0, False, 0, 0.0
        codebase.JOB_HANDLERS[kind](x, ref)

    def performance(self, route, req, max_instructions, max_queries):
        base = TestBed._performance_db()
        db = Database(base)
        x = Execution()
        x.db, x.cod, x.product, x.month = db, self.cod, self, 0
        x.t, x.customer, x.user, x.simulated, x.work_units, x.ext = 60 * MINUTES_PER_DAY, 1, 1, True, 0, 0.0
        codebase.ROUTE_HANDLERS[route](x, req)
        base.set_progress_handler(None, 10)
        assert db.instr <= max_instructions, f"{db.instr} dezenas de instruções"
        assert db.queries <= max_queries, f"{db.queries} consultas"

    @staticmethod
    def _performance_db():
        """A large test database (30 thousand orders), built once and only read."""
        if TestBed._perf_db_cache is None:
            con = create_db([("arroz ensaio", "arroz ensaio", "mercearia", 10.0, 9999, 9999, 1.0)],
                              [(c, f"Loja {c}", f"Loja {c} Ltda", "pro", "30140-071", "MG", 2, None, 0, 1) for c in range(1, 201)],
                              [(1, 1, "maria.ensaio")])
            rows = []
            items = []
            for i in range(30000):
                rows.append((i + 1, 1 + (i * 7) % 200, 1, 50.0, 2, "pago", "30140-071", 60 * MINUTES_PER_DAY - (i * 3) % (90 * MINUTES_PER_DAY)))
                items.append((i + 1, 1, 2, 25.0))
            con.executemany("INSERT INTO pedidos (id, cliente, usuario, valor, itens, estado, cep, t) VALUES (?,?,?,?,?,?,?,?)", rows)
            con.executemany("INSERT INTO itens_pedido (pedido, produto, quantidade, preco) VALUES (?,?,?,?)", items)
            TestBed._perf_db_cache = con
        return TestBed._perf_db_cache


def run_tests(candidate_code, component, rng, coverage, run_all=False):
    """Quality runs the component's tests against the candidate code. Each test runs with probability `coverage` (all of them if
    `run_all`). Returns (tests run, [(function, test, message)] for the failures)."""
    tests = codebase.component_tests(component)
    chosen = [tt for tt in tests if run_all or rng.random() < coverage]
    if not chosen:
        return 0, []
    testbed = TestBed(candidate_code)
    failures = []
    for func_name, name, f, kind in chosen:
        try:
            f(testbed)
        except Exception as e:
            failures.append((func_name, name, f"{type(e).__name__}: {e}"))
    testbed.con.close()
    return len(chosen), failures
