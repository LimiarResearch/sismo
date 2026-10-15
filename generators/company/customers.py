"""The customers: hundreds of businesses (shops, markets, offices) that buy through the platform. Each one has a plan, users, a
CEP, opening hours, usage intensity and satisfaction. Every minute users open sessions and walk through journeys in the product
(log in, browse the catalog, search, fill the cart, quote shipping, place the order, pay, pull a report); each step is a real call
to the product. When the product fails them they retry, give up and, minutes later (human delay), some of them open a support
ticket; they also open tickets for questions, double charges and fiscal notes that never arrived. They answer support when asked,
pay their invoices and cancel when unhappy; new ones come in through sales.

The outside world is random (when each user opens a session, what they look for); what happens inside the product is the code."""
import math

import numpy as np

from .catalog import (ROUTE_COMPONENT, PLANS, DIGIT_REGION, STATES_BY_DIGIT, MINUTES_PER_DAY, rng_for, np_rng)

FIRST_NAMES = ("maria", "ana", "carlos", "paulo", "pedro", "luiz", "rafael", "juliana", "fernanda", "bruno", "camila", "lucas", "patrícia",
         "joão", "josé", "andré", "márcia", "lúcia", "célia", "fábio", "mônica", "inês", "sérgio", "vânia", "conceição", "simão",
         "beatriz", "gustavo", "renata", "marcos", "aline", "diego", "tatiane", "rodrigo", "priscila", "vinícius", "luís", "cláudia")
REGION_WEIGHTS = (("0", 0.17), ("1", 0.13), ("2", 0.10), ("3", 0.14), ("4", 0.07), ("5", 0.07), ("6", 0.06), ("7", 0.10), ("8", 0.10), ("9", 0.06))
PLAN_WEIGHTS = (("básico", 0.58), ("pro", 0.31), ("empresarial", 0.11))
USERS_PER_PLAN = {"básico": (1, 2), "pro": (2, 4), "empresarial": (5, 12)}
TICKET_RATE_BY_PLAN = {"básico": 0.05, "pro": 0.08, "empresarial": 0.14}
PLAN_PRIORITY = {"básico": "baixa", "pro": "média", "empresarial": "alta"}
RAISE_PRIORITY = {"baixa": "média", "média": "alta", "alta": "crítica", "crítica": "crítica"}
WEEKDAY_FACTOR = (1.22, 1.04, 1.0, 0.98, 0.82, 0.0, 0.0)
SESSIONS_PER_USER_MINUTE = 0.0034


def _random_cep(rng, digit):
    return f"{digit}{rng.randint(0, 9999):04d}-{rng.randint(0, 999):03d}"


def _choose(rng, weights):
    r = rng.random()
    acc = 0.0
    for v, p in weights:
        acc += p
        if r < acc:
            return v
    return weights[-1][0]


class Customers:
    def __init__(self, seed, n_initial, null):
        self.rng = rng_for(seed, "clientes")
        self.usage_rng = rng_for(seed, "uso dos clientes")
        self.g = np_rng(seed, "sessoes dos clientes")
        self.null = null
        self.n = 0
        cap = 4096
        self.active = np.zeros(cap, dtype=bool)
        self.users_per_customer = np.zeros(cap)
        self.opens_at = np.zeros(cap)
        self.closes_at = np.zeros(cap)
        self.saturday = np.zeros(cap, dtype=bool)
        self.intensity = np.zeros(cap)
        self.joined = np.zeros(cap)
        self.info = [None]                    # per customer: dict with plan, CEP, users, satisfaction...
        self.user_login = {}
        self.next_user = 1
        self.initial_records = ([], [])     # (customers, users) for the product database
        for _ in range(n_initial):
            self._generate(0, -self.rng.randint(30, 900) * MINUTES_PER_DAY, initial=True)
        self.sessions = {}                     # instant -> [session]
        self.contacts = []                    # scheduled contacts: (instant, sequence, data)
        self._seq = 0
        self.tickets = {}                    # item -> customer-side data of the ticket
        self.open_by = {}                  # (customer, component) -> open item
        self.responses = []                   # (instant, item) customer replies to support
        self.invoice_payments = []           # (instant, customer) for the day
        self.to_cancel = []                    # customers who will ask to cancel ("sem_deriva" null variant)
        self.min = self._empty_counters()
        self.daily_tickets = {p: 0 for p in PLANS}

    # ---------- customer base ----------
    def _generate(self, t, joined, initial=False, plan=None):
        s = self.rng
        self.n += 1
        c = self.n
        if c >= len(self.active):
            for name in ("active", "users_per_customer", "opens_at", "closes_at", "saturday", "intensity", "joined"):
                v = getattr(self, name)
                setattr(self, name, np.concatenate([v, np.zeros_like(v)]))
        plan = plan or _choose(s, PLAN_WEIGHTS)
        digit = _choose(s, REGION_WEIGHTS)
        cep = _random_cep(s, digit)
        uf = s.choice(STATES_BY_DIGIT[digit])
        n_users = s.randint(*USERS_PER_PLAN[plan])
        info = {"plano": plan, "cep": cep, "uf": uf, "regiao": DIGIT_REGION[digit], "usuarios": [],
                "telefone": None if s.random() < 0.3 else f"{s.randint(11, 99)} 3{s.randint(100, 999)}-{s.randint(1000, 9999)}",
                "nome_fantasia": None if s.random() < 0.25 else f"Loja {c:04d}", "satisfacao": s.uniform(0.62, 0.95),
                "frustracoes": [], "dia_pagamento": s.randint(3, 12), "produtos_preferidos": [], "entrada": joined,
                "ativo": True}
        for _ in range(n_users):
            u = self.next_user
            self.next_user += 1
            login = f"{s.choice(FIRST_NAMES)}.loja{c:04d}{u}"
            info["usuarios"].append(u)
            self.user_login[u] = login
            self.initial_records[1].append((u, c, login)) if initial else None
        self.info.append(info)
        self.active[c] = True
        self.users_per_customer[c] = n_users
        self.opens_at[c] = s.randint(7 * 60, 9 * 60 + 30)
        self.closes_at[c] = s.randint(17 * 60, 19 * 60 + 30)
        self.saturday[c] = s.random() < 0.3
        self.intensity[c] = s.lognormvariate(0.0, 0.45)
        self.joined[c] = joined
        reg = (c, info["nome_fantasia"], f"Comércio {c:04d} Ltda", plan, cep, uf, info["regiao"], info["telefone"], joined, 1)
        if initial:
            self.initial_records[0].append(reg)
        return c, reg

    def join(self, t, plan, product, truth):
        """A new customer, coming from a won deal: the administrative staff creates the account in the product."""
        c, reg = self._generate(t, t, plan=plan)
        info = self.info[c]
        product.db.con.execute("INSERT INTO clientes (id, nome_fantasia, razao, plano, cep, uf, regiao, telefone, criado_em, ativo) "
                               "VALUES (?,?,?,?,?,?,?,?,?,?)", reg)
        for u in info["usuarios"]:
            product.db.con.execute("INSERT INTO usuarios (id, cliente, login, ativo) VALUES (?,?,?,1)", (u, c, self.user_login[u]))
        self.min["entradas"] += 1
        truth.portfolio_event(t, "entrada", c, plan)
        if self.null == "sem_deriva":
            # the customer base does not grow: each new customer leads to the most dissatisfied one leaving within two days
            candidates = [(self.info[k]["satisfacao"], k) for k in range(1, self.n) if self.info[k]["ativo"] and k not in self.to_cancel]
            if candidates:
                target = min(candidates)[1]
                self.to_cancel.append(target)
                self._schedule_contact(t + self.rng.randint(60, 2 * MINUTES_PER_DAY), target, "cancelamento", "login", None, "e-mail")
        return c

    def churn(self, t, c, product, truth):
        info = self.info[c]
        if not info["ativo"]:
            return
        info["ativo"] = False
        self.active[c] = False
        product.db.con.execute("UPDATE clientes SET ativo=0 WHERE id=?", (c,))
        product.db.con.execute("UPDATE usuarios SET ativo=0 WHERE cliente=?", (c,))
        self.min["cancelamentos"] += 1
        truth.portfolio_event(t, "saída", c, info["plano"])

    def active_count(self):
        return int(self.active[: self.n + 1].sum())

    @property
    def _n_active(self):
        return self.active_count()

    # ---------- the minute ----------
    def _empty_counters(self):
        return {"sessoes_iniciadas": 0, "abandonos": 0, "entradas": 0, "cancelamentos": 0, "contatos": {"chat": 0, "e-mail": 0, "telefone": 0},
                "chamados_plano": {p: 0 for p in PLANS}, "pesquisas": [], "faturas_pagas": 0}

    def minute(self, t, cal, product, workflow, truth, shuffled):
        self.min = self._empty_counters()
        self._new_sessions(t, cal)
        if cal.workday and 2 <= cal.day_of_month <= 5 and 9 * 60 <= cal.minute < 16 * 60 and self.rng.random() < self._n_active * 0.012 / 420.0:
            actives = [c for c in range(1, self.n + 1) if self.info[c]["ativo"]]
            c = self.rng.choice(actives)
            self._schedule_contact(t + self.rng.randint(1, 30), c, "fatura", "pagamento", None, None)
        self._steps(t, cal, product, truth)
        self._contacts(t, cal, workflow, truth)
        self._replies(t, cal, workflow)
        while self.invoice_payments and self.invoice_payments[0][0] <= t:
            _, c = self.invoice_payments.pop(0)
            n = product.db.con.execute("UPDATE faturas SET estado='paga' WHERE cliente=? AND estado='aberta'", (c,)).rowcount
            self.min["faturas_pagas"] += n

    def _new_sessions(self, t, cal):
        n = self.n + 1
        m = cal.minute
        ds = cal.weekday
        if ds < 5:
            inside = (self.opens_at[:n] <= m) & (m < self.closes_at[:n])
            hour = m / 60.0
            profile = 1.0 + 0.28 * math.exp(-((hour - 10.3) ** 2) / 1.2) + 0.22 * math.exp(-((hour - 15.2) ** 2) / 1.5)
            if 12 * 60 <= m < 13 * 60 + 30:
                profile *= 0.55
            factor = np.where(inside, profile * WEEKDAY_FACTOR[ds], 0.035)
        elif ds == 5:
            factor = np.where(self.saturday[:n] & (8 * 60 <= m) & (m < 12 * 60), 0.6, 0.03)
        else:
            factor = 0.02
        if cal.end_of_month():
            factor = factor * 1.12
        days = (t - self.joined[:n]) / MINUTES_PER_DAY
        ramp = np.clip(0.3 + 0.07 * days, 0.3, 1.0)
        lam = SESSIONS_PER_USER_MINUTE * self.users_per_customer[:n] * self.intensity[:n] * factor * ramp * self.active[:n]
        new_counts = self.g.poisson(lam)
        for c in np.flatnonzero(new_counts):
            for _ in range(int(new_counts[c])):
                self._open_session(t, int(c), cal)

    def _open_session(self, t, c, cal):
        s = self.usage_rng
        info = self.info[c]
        u = s.choice(info["usuarios"])
        r = s.random()
        month_end = cal.end_of_month()
        if r < (0.42 if not month_end else 0.46):
            kind = "compra"
        elif r < (0.72 if not month_end else 0.68):
            kind = "consulta"
        elif r < (0.87 if not month_end else 0.90):
            kind = "gestao"
        elif r < 0.93:
            kind = "conta"
        else:
            kind = "recompra"
        steps = [("login", {"login": self.user_login[u]})]
        cat = s.choice(self.categories)
        if kind in ("compra", "consulta"):
            for page in range(1, s.choice((1, 1, 1, 2, 2, 3, 4)) + 1):
                steps.append(("catalogo", {"categoria": cat, "pagina": page}))
            for _ in range(s.choice((0, 1, 1, 2) if kind == "compra" else (1, 1, 2, 3))):
                steps.append(("busca", {"termo": self._search_term(s)}))
            for _ in range(s.randint(1, 3)):
                steps.append(("produto", {"produto": s.randint(1, self.n_products)}))
        if kind in ("compra", "recompra"):
            items = []
            favorites = info["produtos_preferidos"]
            for _ in range(s.randint(1, 4) if kind == "compra" else s.randint(2, 6)):
                if kind == "recompra" and favorites:
                    p = s.choice(favorites)
                else:
                    p = s.randint(1, self.n_products)
                q = s.random()
                qty = str(s.randint(1, 9)) if q < 0.68 else (str(s.randint(10, 99)) if q < 0.96 else str(s.randint(100, 400)))
                items.append((p, qty))
                steps.append(("carrinho", {"produto": p, "quantidade": qty}))
            steps.append(("frete", {"cep": info["cep"], "peso": round(s.uniform(0.5, 30.0), 1)}))
            steps.append(("pedido", {"itens": items, "cep": info["cep"]}))
            steps.append(("pagamento", None))
        if kind == "gestao":
            steps.append(("relatorio", {"dias": 30}))
            if s.random() < 0.5:
                steps.append(("exportacao", {"dias": 30}))
            if s.random() < 0.6:
                steps.append(("notas", {}))
        if kind == "conta":
            steps.append(("conta", {"telefone": info["telefone"], "nome_fantasia": info["nome_fantasia"]}))
        # session: [customer, user, steps, index, order created, slowness felt]
        self.sessions.setdefault(t, []).append([c, u, steps, 0, None, False])
        self.min["sessoes_iniciadas"] += 1

    def _search_term(self, s):
        word = s.choice(self.words)
        if s.random() < 0.3:
            word = word.translate(STRIP_ACCENTS)
        return word

    def _steps(self, t, cal, product, truth):
        entries = self.sessions.pop(t, None)
        if not entries:
            return
        s = self.usage_rng
        for sess in entries:
            c, u, steps, i, order, slow = sess
            info = self.info[c]
            if not info["ativo"]:
                continue
            route, req = steps[i]
            if route == "pagamento":
                if order is None:
                    continue
                req = {"pedido": order}
            state, lat, failed_fn = product.call(t, route, req, c, u)
            attempts = 0
            while state == "erro" and attempts < 2:            # the user retries
                attempts += 1
                state, lat, failed_fn = product.call(t, route, req, c, u)
            if state == "erro":
                self.min["abandonos"] += 1
                self._frustrate(t, c, route, failed_fn, truth, "erro")
                continue
            if lat > 4000.0 and not slow:
                sess[5] = True
                if s.random() < 0.35:
                    self._frustrate(t, c, route, None, truth, "lentidão")
            if state == "recusa":
                if route in ("login", "pedido") or (route == "pagamento" and s.random() < 0.5):
                    continue                                        # gives up for today
                if route == "pagamento":
                    state2, _, _ = product.call(t, route, req, c, u)  # tries another card
                    if state2 != "ok":
                        continue
            if route == "pedido" and state == "ok":
                r = product.db.con.execute("SELECT MAX(id) FROM pedidos WHERE cliente=? AND t=?", (c, t)).fetchone()
                sess[4] = r[0]
                pref = info["produtos_preferidos"]
                for p, _ in req["itens"]:
                    if p not in pref:
                        pref.append(p)
                del pref[:-12]
            if route == "pagamento" and state == "ok" and s.random() < 0.05:
                state2, _, _ = product.call(t, route, req, c, u)  # the double click
                if state2 == "ok":                                  # charged twice: the customer notices on the statement
                    if s.random() < 0.6:
                        self._schedule_contact(t + int(s.lognormvariate(math.log(900), 0.6)), c, "cobrança em dobro", "pagamento",
                                             ("registrar_cobranca", t), None)
            i += 1
            if i >= len(steps):
                if s.random() < (0.010 if t - info["entrada"] > 14 * MINUTES_PER_DAY else 0.04):
                    route_d = s.choice(steps)[0]
                    self._schedule_contact(t + int(s.lognormvariate(math.log(25), 0.7)), c, "dúvida", ROUTE_COMPONENT[route_d], None, None)
                continue
            sess[3] = i
            wait = 1
            while s.random() < 0.38 and wait < 6:
                wait += 1
            self.sessions.setdefault(t + wait, []).append(sess)

    # ---------- frustration and tickets ----------
    def _frustrate(self, t, c, route, failed_fn, truth, kind):
        info = self.info[c]
        s = self.usage_rng
        info["satisfacao"] = max(0.0, info["satisfacao"] - 0.012)
        frustrations = info["frustracoes"]
        frustrations.append(t)
        while frustrations and frustrations[0] < t - MINUTES_PER_DAY:
            frustrations.pop(0)
        comp = ROUTE_COMPONENT[route]
        opened = self.open_by.get((c, comp))
        p = min(0.7, TICKET_RATE_BY_PLAN[info["plano"]] * (1.0 + 0.5 * (len(frustrations) - 1)))
        if kind == "lentidão":
            p *= 0.6
        if opened is not None:
            if s.random() < 0.2:
                self.responses.append((t + int(s.lognormvariate(math.log(15), 0.6)), opened, "comentário"))
            return
        if s.random() < p:
            delay = int(s.lognormvariate(math.log(12), 0.75)) + 1
            self._schedule_contact(t + delay, c, "erro" if kind == "erro" else "lentidão", comp, (failed_fn, t), None)

    def _schedule_contact(self, when, c, reason, comp, cause, channel):
        self._seq += 1
        self.contacts.append((when, self._seq, (c, reason, comp, cause, channel)))
        self.contacts.sort()
        if reason != "cancelamento":
            self.open_by.setdefault((c, comp), -1)

    def _contacts(self, t, cal, workflow, truth):
        while self.contacts and self.contacts[0][0] <= t:
            _, _, (c, reason, comp, cause, channel) = self.contacts.pop(0)
            info = self.info[c]
            if not info["ativo"]:
                self.open_by.pop((c, comp), None)
                continue
            s = self.usage_rng
            working_hours = cal.workday and 8 * 60 <= cal.minute < 18 * 60
            if channel is None:
                r = s.random()
                channel = "chat" if r < 0.5 else ("e-mail" if r < 0.85 else "telefone")
            if not working_hours and channel != "e-mail":
                channel = "e-mail"
            priority = PLAN_PRIORITY[info["plano"]]
            if reason in ("erro", "cobrança em dobro") and comp in ("pedido", "pagamento", "login"):
                priority = RAISE_PRIORITY[priority]
            title = {"erro": f"erro ao usar {comp}", "lentidão": f"lentidão em {comp}", "dúvida": f"dúvida sobre {comp}",
                      "cobrança em dobro": "cobrança em dobro no cartão", "nota não emitida": "nota fiscal não chegou",
                      "fatura": "dúvida sobre a fatura", "cancelamento": "pedido de cancelamento"}[reason]
            item = workflow.create(t, "SUP", "chamado", title, priority=priority, component=comp, team="atendimento", actor="cliente",
                               customer=c, channel=channel, origin="cliente")
            self.tickets[item] = {"cliente": c, "motivo": reason, "componente": comp, "causa": cause, "criado": t, "plano": info["plano"]}
            if reason != "cancelamento":
                self.open_by[(c, comp)] = item
            self.min["contatos"][channel] += 1
            self.min["chamados_plano"][info["plano"]] += 1
            truth.ticket_opened(t, item, c, reason, comp, cause)

    def ticket_resolved(self, t, item):
        d = self.tickets.get(item)
        if d is None:
            return
        info = self.info[d["cliente"]]
        dur = t - d["criado"]
        info["satisfacao"] = min(1.0, max(0.0, info["satisfacao"] + (0.02 if dur < 240 else (-0.03 if dur > 2 * MINUTES_PER_DAY else 0.0))))
        if self.open_by.get((d["cliente"], d["componente"])) == item:
            del self.open_by[(d["cliente"], d["componente"])]

    def ticket_closed(self, t, item):
        d = self.tickets.pop(item, None)
        if d is None:
            return
        if self.open_by.get((d["cliente"], d["componente"])) == item:
            del self.open_by[(d["cliente"], d["componente"])]
        s = self.usage_rng
        if s.random() < 0.3:
            info = self.info[d["cliente"]]
            dur = t - d["criado"]
            score = 2.0 + 3.0 * info["satisfacao"] - (1.0 if dur > 2 * MINUTES_PER_DAY else 0.0) + s.uniform(-0.6, 0.6)
            self.min["pesquisas"].append(max(1.0, min(5.0, round(score))))

    def ask_customer(self, t, item, cal):
        """Support asked the customer something; the customer answers later (during their own hours)."""
        s = self.usage_rng
        self.responses.append((t + int(s.lognormvariate(math.log(70), 0.9)) + 5, item, "resposta"))

    def _replies(self, t, cal, workflow):
        if not self.responses:
            return
        pending = []
        for when, item, kind in self.responses:
            if when > t:
                pending.append((when, item, kind))
                continue
            d = self.tickets.get(item)
            if d is None:
                continue
            c = d["cliente"]
            m = cal.minute
            if not (cal.workday and self.opens_at[c] <= m < self.closes_at[c] + 60):
                pending.append((t + 30, item, kind))              # answers when the shop opens
                continue
            if kind == "resposta":
                r = workflow.item(item)
                if r is not None and r["estado"] == "aguardando cliente":
                    workflow.transition(t, item, "em atendimento", "cliente")
                    workflow.assign_to(item, None)
                    workflow.comment(t, item, "cliente", "o cliente respondeu")
            else:
                r = workflow.item(item)
                if r is not None and r["estado"] not in ("resolvido", "fechado", "descartado"):
                    workflow.comment(t, item, "cliente", "o cliente voltou a escrever: o problema continua")
        self.responses = pending

    # ---------- the day ----------
    def new_date(self, t, cal):
        """When the calendar date changes: who pays the invoice on this date."""
        s = self.rng
        self.invoice_payments = []
        if not cal.workday:
            return
        for c in range(1, self.n + 1):
            info = self.info[c]
            if info["ativo"] and (cal.day_of_month == info["dia_pagamento"] or (cal.day_of_month > info["dia_pagamento"] and s.random() < 0.15)):
                self.invoice_payments.append((t + max(0, s.randint(8 * 60, 17 * 60) - cal.minute), c))
        self.invoice_payments.sort()

    def lived_day(self, t, cal, product, truth):
        """Once per lived day: satisfaction, cancellations, fiscal notes that did not arrive."""
        s = self.rng
        actives = [c for c in range(1, self.n + 1) if self.info[c]["ativo"]]
        for c in actives:
            info = self.info[c]
            info["satisfacao"] += 0.01 * (0.8 - info["satisfacao"])
            if cal.workday:
                h = 0.0005 * (1.0 + 30.0 * max(0.0, 0.7 - info["satisfacao"]) ** 2)
                if s.random() < h and c not in self.to_cancel:
                    self.to_cancel.append(c)
                    self._schedule_contact(t + s.randint(9 * 60, 15 * 60) - cal.minute, c, "cancelamento", "login", None, None)
        if cal.workday:
            # shops check whether the fiscal notes for yesterday's and the day before's orders arrived
            try:
                missing_notes = product.db.con.execute(
                    "SELECT p.cliente, COUNT(*) FROM pedidos p LEFT JOIN notas n ON n.pedido = p.id WHERE p.t >= ? AND p.t < ? "
                    "AND n.id IS NULL AND p.cliente > 0 GROUP BY p.cliente", (t - 3 * MINUTES_PER_DAY, t - MINUTES_PER_DAY)).fetchall()
            except Exception:
                missing_notes = []
            for c, n in missing_notes:
                if self.info[c]["ativo"] and (c, "fiscal") not in self.open_by and s.random() < 0.3:
                    self._schedule_contact(t + s.randint(9 * 60, 16 * 60) - cal.minute, c, "nota não emitida", "fiscal", ("emitir_nota", t), None)

    def counts(self):
        """For the connectors: active customers per plan and per region, active sessions per plan, connected users."""
        n = self.n + 1
        by_plan = {p: 0 for p in PLANS}
        by_region = [0] * 6
        for c in range(1, n):
            info = self.info[c]
            if info["ativo"]:
                by_plan[info["plano"]] += 1
                by_region[info["regiao"]] += 1
        sessions_by_plan = {p: 0 for p in PLANS}
        users = set()
        total = 0
        for entries in self.sessions.values():
            for sess in entries:
                sessions_by_plan[self.info[sess[0]]["plano"]] += 1
                users.add(sess[1])
                total += 1
        return by_plan, by_region, sessions_by_plan, len(users), total


STRIP_ACCENTS = str.maketrans("áàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇ", "aaaaeeiooouucAAAAEEIOOOUUC")
