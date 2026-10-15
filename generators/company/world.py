"""The World class: the interface to the simulated company (see CONTRACT.md).

The world is the whole company running in time: the clock, the live product with its database, job queue and disk, the version
repository, the workflow tracker, the CRM, the calendar, the staff board, the customers and the 50 people. Each call to step()
makes one minute happen (people act, customers hit the product, the code runs, the databases change) and returns the measures of
every process in that minute. The world only moves when step() is called.

Usage:
    from generators.company import World
    m = World(1)
    for p in m.processes(): ...
    values = m.step()            # minute 1
    m.save("folder"); m2 = World.load("folder")
"""
import os
import pickle
import sqlite3
from dataclasses import dataclass, field

from .catalog import TEAMS, PLANS, MINUTES_PER_DAY, rng_for
from .clock import Clock
from .customers import Customers
from .product import Product
from .workflow import Workflow
from .repository import Repository
from .crm import CRM
from .agenda import Agenda
from .board import StaffBoard
from .truth import Truth
from .acts import ActsInbox
from .people import Company, PLAN_VALUE, SQUAD_COMPONENTS, THEMES
from .connectors import Connectors

NULLS = (None, "sem_defeito", "embaralhado", "sem_deriva", "surdo")
PAGES_PER_CUSTOMER_DAY = 0.62       # database growth per customer per day that operations estimated when sizing the volume
DATABASES = ("produto", "fluxo", "repositorio", "crm", "agenda", "quadro")


@dataclass(frozen=True)
class Process:
    name: str
    fields: list = field(default_factory=list)


class World:
    def __init__(self, seed: int, null: str | None = None, real_time: bool = False):
        if null not in NULLS:
            raise ValueError(f"unknown null variant: {null}; the null variants are {', '.join(n for n in NULLS if n)}")
        self.seed = int(seed)
        self.null = null
        self.clock = Clock(self.seed, shuffled=(null == "embaralhado"), real_time=real_time)
        setup_rng = rng_for(self.seed, "partida")
        self.customers = Customers(self.seed, setup_rng.randint(380, 440), null)
        records, users = self.customers.initial_records
        self.customers.initial_records = ([], [])
        headroom = setup_rng.uniform(9.0, 24.0)
        self.product = Product(self.seed, records, users, PAGES_PER_CUSTOMER_DAY * len(records), headroom)
        self.customers.categories = list(self.product.categories)
        self.customers.n_products = len(self.product.initial_products)
        words = sorted({w for name, *_ in self.product.initial_products for w in name.split() if len(w) > 3 and not w[0].isdigit()})
        self.customers.words = words
        self.workflow = Workflow()
        self.repo = Repository()
        self.crm = CRM()
        self.agenda = Agenda()
        self.board = StaffBoard()
        self.recorder = Truth(self.seed, null)
        self.recorder.initial_volume_headroom_days = round(headroom, 1)
        self.inbox = ActsInbox(deaf=(null == "surdo"))
        self.events = []
        self.sis = {"produto": self.product, "fluxo": self.workflow, "repo": self.repo, "crm": self.crm, "agenda": self.agenda,
                    "quadro": self.board, "clientes": self.customers, "verdade": self.recorder, "porta": self.inbox,
                    "eventos": self.events, "relogio": self.clock, "estornos": [0]}
        self.company = Company(self.seed, null, self.sis)
        self.connectors = Connectors()
        self.market = rng_for(self.seed, "mercado")
        self.referrals = []
        self.next_lived_day = 0
        self.day_rng = rng_for(self.seed, "dias vividos")
        self._initial_state()
        self._processes = [Process(n, list(c)) for n, c in self.connectors.processes]

    # ======================================================================================================== the interface
    @property
    def t(self):
        return self.clock.t

    def day(self):
        return self.clock.day()

    def minute_of_day(self):
        return self.clock.minute_of_day()

    def day_of_week(self):
        return self.clock.day_of_week()

    def processes(self):
        return [Process(p.name, list(p.fields)) for p in self._processes]

    def teams(self):
        return list(TEAMS)

    def step(self):
        clk = self.clock
        new_day = clk.advance()
        t = clk.t
        cal = clk.cal
        clk.wait_wall_clock()
        sis = self.sis
        self.inbox.materialize(t, cal, sis)
        if new_day:
            if not clk.shuffled or t >= self.next_lived_day:
                self._lived_day(t, cal)
                if clk.shuffled:
                    self.next_lived_day = t + self.day_rng.randint(720, 2160)
            self._new_date(t, cal)
        if cal.minute % 60 == 5:
            self._automations(t)
        prod = self.product
        prod.run_scheduled_jobs(t, cal)
        prod.process_queue(t, cal.month)
        self.customers.minute(t, cal, prod, self.workflow, self.recorder, clk.shuffled)
        self._market(t, cal)
        self.company.minute(t, cal)
        self.inbox.expire(t, sis)
        prod.run_probe(t)
        errors = []
        for e in reversed(prod.errors):
            if e[0] != t:
                break
            errors.append(e)
        if errors:
            self.recorder.minute_errors(t, errors)
        tallies = prod.close_minute(t, cal)
        self.recorder.probe_minute(t, tallies["sonda"][1] >= 6, prod)
        self.recorder.record_latency(t, cal, tallies["rotas"])
        return self.connectors.read(t, cal, self, tallies)

    def receive(self, team: str, kind: str, text: str) -> int:
        return self.inbox.receive(team, kind, text)

    def responses(self):
        return self.inbox.responses()

    def truth(self) -> dict:
        """For the benchmark only: what the company has and when it happened, up to the current minute."""
        return self.recorder.as_dict(self.clock, self.clock.shuffled)

    def human_events(self):
        return list(self.events)

    # ======================================================================================================== pause and resume
    def _databases(self):
        return {"produto": self.product.db.con, "fluxo": self.workflow.db, "repositorio": self.repo.db, "crm": self.crm.db,
                "agenda": self.agenda.db, "quadro": self.board.db}

    def save(self, folder):
        os.makedirs(folder, exist_ok=True)
        for name, con in self._databases().items():
            file_path = os.path.join(folder, name + ".sqlite")
            if os.path.exists(file_path):
                os.remove(file_path)
            dest = sqlite3.connect(file_path)
            con.backup(dest)
            dest.close()
        with open(os.path.join(folder, "estado.pickle"), "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load(folder):
        with open(os.path.join(folder, "estado.pickle"), "rb") as f:
            m = pickle.load(f)
        cons = {}
        for name in DATABASES:
            mem = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False,
                                  cached_statements=0 if name == "produto" else 128)
            origin = sqlite3.connect(os.path.join(folder, name + ".sqlite"))
            origin.backup(mem)
            origin.close()
            cons[name] = mem
        m.product.connect(cons["produto"])
        m.workflow.attach_db(cons["fluxo"])
        m.repo.db = cons["repositorio"]
        m.crm.attach_db(cons["crm"])
        m.agenda.db = cons["agenda"]
        m.board.db = cons["quadro"]
        return m

    def __getstate__(self):
        return dict(self.__dict__)

    # ======================================================================================================== what drives the world from outside
    def _new_date(self, t, cal):
        """The calendar date changed: attendance plans, agenda, daily counters."""
        self.company.new_date(t, cal)
        self.customers.new_date(t, cal)
        self.agenda.prune(t, cal, self.clock.shuffled)
        self.connectors.new_day()
        self.recorder.new_date(t, cal)

    def _automations(self, t):
        """The hourly workflow automation: a ticket resolved two days ago closes by itself."""
        for r in self.workflow.db.execute("SELECT id FROM itens WHERE projeto='SUP' AND tipo='chamado' AND estado='resolvido' AND resolvido_em < ? ORDER BY id",
                                       (t - 2 * MINUTES_PER_DAY,)).fetchall():
            self.workflow.transition(t, r[0], "fechado", "atendimento")
            self.customers.ticket_closed(t, r[0])

    def _lived_day(self, t, cal):
        """Once per lived day: what has a daily rate (sickness, resignation, cancellation, referral)."""
        self.company.lived_day(t, cal)
        self.customers.lived_day(t, cal, self.product, self.recorder)
        self.recorder.lived_day(t, self.customers.active_count())
        # today's referrals: satisfied customers recommend the platform to people they know
        self.referrals = []
        if cal.workday:
            n = self.customers.active_count()
            satisfaction = [self.customers.info[c]["satisfacao"] for c in range(1, self.customers.n + 1) if self.customers.info[c]["ativo"]]
            avg = sum(satisfaction) / len(satisfaction) if satisfaction else 0.7
            expected = 0.6 * n / 400.0 * (avg / 0.8) ** 2
            k = int(expected) + (1 if self.market.random() < expected - int(expected) else 0)
            for _ in range(k):
                self.referrals.append(t + self.market.randint(8 * 60, 18 * 60) - cal.minute)
            self.referrals.sort()

    def _market(self, t, cal):
        """Leads arriving through the website (more in business hours, proportional to the size of the customer base) and referrals."""
        s = self.market
        n = self.customers.active_count() if t % 60 == 0 or not hasattr(self, "_n_cache") else self._n_cache
        self._n_cache = n
        lam = (0.0016 if (cal.workday and 8 * 60 <= cal.minute < 20 * 60) else 0.00025) * n / 400.0
        if s.random() < lam:
            plan = _random_plan(s)
            self.crm.new_deal(t, "site", plan, PLAN_VALUE[plan], next_at=t + s.randint(10, 180))
        while self.referrals and self.referrals[0] <= t:
            self.referrals.pop(0)
            plan = _random_plan(s)
            self.crm.new_deal(t, "indicação", plan, PLAN_VALUE[plan], next_at=t + s.randint(10, 120))

    def _initial_state(self):
        """The company already exists at instant 0: backlog, previous sprints, sales funnel, epics in progress."""
        s = rng_for(self.seed, "estado inicial")
        workflow = self.workflow
        company = self.company
        for project in ("PROD", "PLAT"):
            comps = SQUAD_COMPONENTS[project]
            for state, n in (("backlog", 14), ("refinamento", 5), ("pronto para desenvolver", 16)):
                for _ in range(n):
                    comp = s.choice(comps)
                    kind = "história" if s.random() < 0.8 else "tarefa"
                    est = state if kind == "história" or state != "refinamento" else "backlog"
                    workflow.create(-s.randint(60, 40 * MINUTES_PER_DAY), project, kind, s.choice(THEMES[comp]),
                                priority=s.choice(("baixa", "média", "média", "média", "alta")), component=comp,
                                team="desenvolvimento", actor="produto", points=s.choice((1, 2, 3, 3, 5, 8)), state=est)
            for _ in range(3):
                comp = s.choice(comps)
                workflow.create(-s.randint(60, 20 * MINUTES_PER_DAY), project, "bug", f"comportamento estranho em {comp}", priority="média",
                            component=comp, team="desenvolvimento", actor="atendimento", points=s.choice((1, 2)),
                            state="pronto para desenvolver", origin="atendimento")
            # the first roadmap epic, already refined
            company._finish_roadmap_epic(None, {"projeto": project}, 0, None)
            ep = company.active_epic[project]
            stories = workflow.items(project=project, kind="história", extra=f" AND epico={ep}")
            for i, r in enumerate(stories):
                # the epic was already under way: the first stories were released before the start
                done = i < len(stories) - 3 and r["id"] not in company.feature_story
                workflow.transition(0, r["id"], "liberado" if done else "pronto para desenvolver", "produto")
        for _ in range(5):
            workflow.create(-s.randint(60, 30 * MINUTES_PER_DAY), "INFRA", "tarefa", s.choice(THEMES["infra"]), priority="média",
                        component="infra", team="operação", actor="operação", points=s.choice((1, 2, 3)))
        execs = [p for p in company.people if p.role == "executivo de vendas"]
        for stage, n in (("lead", 6), ("qualificação", 5), ("proposta", 5), ("negociação", 4)):
            for i in range(n):
                plan = _random_plan(s)
                nid = self.crm.new_deal(-s.randint(60, 20 * MINUTES_PER_DAY), s.choice(("site", "site", "indicação", "prospecção")), plan,
                                    PLAN_VALUE[plan], stage=stage, next_at=s.randint(9 * 60, 3 * MINUTES_PER_DAY))
                if stage != "lead":
                    self.crm.assign(nid, execs[i % len(execs)].id)


def _random_plan(s):
    r = s.random()
    return "básico" if r < 0.55 else ("pro" if r < 0.87 else "empresarial")

