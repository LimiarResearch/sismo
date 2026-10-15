"""The 50 people of the company, as agents with a role, a team, working hours and their own way of working. Each one arrives,
has lunch, goes to meetings, leaves (sometimes stays late), misses days, takes vacations; and, when free, picks the next piece of
work for their role and does it in the systems:

- product: keeps the roadmap of epics, opens and refines stories, turns commitments to customers into epics with deadlines;
- development: pulls sprint items, comments, commits code (with a defect chance that grows with rush and item size), reviews
  colleagues' code, investigates and fixes bugs, triages;
- quality: tests (runs the real tests against the branch code), approves, rejects, runs the regression before releases;
- support: answers tickets in deadline order, asks the customer, escalates to development, resolves, closes;
- sales: works the funnel in the CRM (calls, demos, proposals, negotiation), prospects, closes more at the end of the month;
- operations: releases versions on Tuesday and Thursday afternoons, hotfixes, rolls back, handles alerts and on-call duty, handles
  the incident;
- management: finance creates accounts and processes cancellations and refunds; HR hires; the owner calls meetings and makes
  commitments.

Nothing here looks at the ground truth: people only know what the systems show (the workflow tracker, the CRM, the alerts and the
product error log, the tests that run)."""
import math

from . import codebase
from .product import run_tests
from .catalog import (COMPOSITION, ROUTE_COMPONENT, COMPONENT_PROJECT, MINUTES_PER_DAY, rng_for, COMPONENT_NAME)
from .workflow import FINAL_STATES
from .crm import OPEN_STAGES

MINUTES_PER_POINT = 420.0
ROLE_GROUP = {"líder de produto": "produto", "gerente de produto": "produto", "designer": "produto", "analista de produto": "produto",
         "líder técnico": "dev", "desenvolvedor": "dev", "analista de qualidade": "qa", "coordenador de atendimento": "atendimento",
         "analista de atendimento": "atendimento", "gerente de vendas": "vendas", "pré-vendas": "sdr", "executivo de vendas": "vendas",
         "engenheiro de operação": "ops", "financeiro": "financeiro", "pessoas": "rh", "administrativo": "financeiro", "dono": "dono"}
SQUAD_COMPONENTS = {"PROD": ("catalogo", "pedido", "frete", "pagamento", "relatorio"), "PLAT": ("login", "fiscal", "notificacao")}
PRIO_RANK = {"crítica": 0, "alta": 1, "média": 2, "baixa": 3}
PRIO_ORDER_SQL = "CASE prioridade WHEN 'crítica' THEN 0 WHEN 'alta' THEN 1 WHEN 'média' THEN 2 ELSE 3 END"
THEMES = {"catalogo": ("filtro por marca no catálogo", "ordenação por preço", "fotos maiores no produto", "selo de novidade"),
         "pedido": ("observação no pedido", "pedido mínimo por fornecedor", "repetir pedido anterior", "resumo do carrinho"),
         "frete": ("prazo de entrega na cotação", "frete grátis acima de um valor", "retirada no balcão"),
         "pagamento": ("boleto parcelado", "pagamento por pix", "comprovante no e-mail"),
         "relatorio": ("relatório por fornecedor", "gráfico de compras do mês", "filtro por período"),
         "login": ("lembrar o usuário", "troca de senha pelo celular", "perfis de acesso"),
         "fiscal": ("reenvio da nota", "nota com observação", "cancelamento de nota"),
         "notificacao": ("aviso de entrega", "resumo semanal por e-mail", "alerta de estoque baixo"),
         "infra": ("ajustar alertas do servidor", "atualizar o sistema operacional", "revisar cópias de segurança",
                   "rodar ensaio de recuperação", "atualizar certificados", "limpar imagens antigas")}

# The method each role group uses to choose its next piece of work, and the method that finishes each kind of task. The keys
# are the group and task-kind values kept in each person's state.
CHOOSER = {"atendimento": "_choose_support", "dev": "_choose_dev", "dono": "_choose_owner", "financeiro": "_choose_finance",
           "ops": "_choose_ops", "produto": "_choose_product", "qa": "_choose_qa", "rh": "_choose_hr", "sdr": "_choose_sdr",
           "vendas": "_choose_sales"}
FINISHER = {"alerta": "_finish_alert", "ato": "_finish_act", "buscar_candidatos": "_finish_source_candidates",
            "chamado": "_finish_ticket", "corrigir": "_finish_fix", "corrigir_no_ar": "_finish_hotfix",
            "desenvolver": "_finish_develop", "epico_compromisso": "_finish_commitment_epic",
            "epico_roteiro": "_finish_roadmap_epic", "fechar_vaga": "_finish_close_opening",
            "historia_avulsa": "_finish_standalone_story", "incidente": "_finish_incident", "interno": "_finish_internal",
            "investigar": "_finish_investigate", "liberar": "_finish_release", "ligar_lead": "_finish_call_lead",
            "marcar_entrevista": "_finish_schedule_interview", "negocio": "_finish_deal", "prospectar": "_finish_prospect",
            "refinar": "_finish_refine", "regressao": "_finish_regression", "resolver_escalado": "_finish_resolve_escalated",
            "reverter": "_finish_rollback", "revisar": "_finish_review", "solicitacao": "_finish_request",
            "tarefa_infra": "_finish_infra_task", "tarefa_simples": "_finish_simple_task", "testar": "_finish_test",
            "triagem": "_finish_triage", "triar": "_finish_screen", "preparar": "_finish_prepare"}


class Person:
    def __init__(self, ident, team, role, project, seed, hired_at=0):
        s = rng_for(seed, "pessoa", ident)
        self.id = ident
        self.team, self.role, self.project, self.group = team, role, project, ROLE_GROUP[role]
        self.s = s
        self.start = int(max(7 * 60 + 15, min(10 * 60, s.gauss(8 * 60 + 45, 35))))
        self.lunch = int(s.gauss(12 * 60 + 5, 25))
        self.friday_early = s.choice((0, 0, 30, 45, 60))
        self.speed = s.lognormvariate(0.0, 0.18)
        self.sloppiness = s.lognormvariate(0.0, 0.3)       # the larger, the more defects slip through
        self.coverage = s.uniform(0.42, 0.62)           # for testers: how much of the suite they usually run
        self.active = True
        self.hired_at = hired_at
        self.quits_at = None                              # notice period: instant of departure
        self.vacation = set()                             # calendar dates
        self.sick_until = -1
        self.present = False
        self.date = None
        self.arrives_at = self.leaves_at = self.lunch_start = self.lunch_end = 0
        self.absent = None
        self.overtime_until = 0
        self.overtime_decided = False
        self.task = None
        self.suspended = None
        self.idle_until = 0
        self.recent_overtime = []                       # (date, minutes)
        self.remote_since = None


class Company:
    def __init__(self, seed, null, sis):
        self.seed = seed
        self.null = null
        self.sis = sis                                   # the systems and the clock (a dict)
        self.s = rng_for(seed, "decisões da empresa")
        self.people = []
        self.next_id = 1
        for team, role, n, project in COMPOSITION:
            for _ in range(n):
                self._new_person(0, team, role, project)
        self.haste = {"PROD": 1.0, "PLAT": 1.0}
        self.dev_velocity = {"PROD": 0.6, "PLAT": 0.6}     # points per person per workday, measured over sprints
        self.active_epic = {"PROD": None, "PLAT": None}
        self.next_feature = {"PROD": 0, "PLAT": 0}
        self.feature_story = {}                          # item -> (function, implementation, route, title)
        self.commitments = []
        self.author = {}                                  # item -> person who developed it
        self.rejections = {}                            # item -> functions that failed
        self.remaining = {}                               # item -> minutes of work still left
        self.incident = None
        self.alerts = {}
        self.silenced = {}
        self.runbook = False
        self.support_focus = (None, 0)
        self.sales_focus = 0
        self.on_end = {}                                 # meeting -> action when it ends
        self.running_before = ()
        self.sprint_number = {"PROD": 0, "PLAT": 0, "SUP": 0, "INFRA": 0}
        self.last_planning = {}
        self.dev_on_call = None
        self.release_done = set()
        self.last_regression = {}
        self.last_release = -10 ** 9
        self.hotfix = []                                 # approved bugs that call for a hotfix
        self.rollback_to = None
        self.growth_opening_at = -10 ** 9
        self.high_queue_days = 0
        self.commitment_month = -1
        self.alignment_day = -1
        self.escalations_today = 0
        self.planned_load = {}
        self._initial_plan()

    # ======================================================================================================== people
    def _new_person(self, t, team, role, project):
        p = Person(self.next_id, team, role, project, self.seed, t)
        self.next_id += 1
        self.people.append(p)
        self.sis["quadro"].admit(t, p.id, team, role, project)
        return p

    def active_people(self):
        return [p for p in self.people if p.active]

    def team_members(self, team, role=None, project=None):
        return [p for p in self.people if p.active and p.team == team and (role is None or p.role == role)
                and (project is None or p.project == project)]

    def leader(self, project):
        for p in self.people:
            if p.active and p.role == "líder técnico" and p.project == project:
                return p
        devs = self.team_members("desenvolvimento", project=project)
        return devs[0] if devs else None

    def owner(self):
        for p in self.people:
            if p.role == "dono":
                return p
        return None

    def _initial_plan(self):
        """The state of the company on its first day: vacations already booked, one notice period, one hiring in progress, one
        commitment with a deadline, the first epic of each squad."""
        s = self.s
        board = self.sis["quadro"]
        for p in self.people:
            # about thirty vacation days per year, in blocks; drawn for the next four hundred days
            for _ in range(2):
                if s.random() < 0.55:
                    begin = s.randrange(0, 400)
                    begin -= begin % 7
                    for d in range(begin, begin + s.choice((12, 14, 19))):
                        p.vacation.add(d)
        prod_devs = [p for p in self.people if p.role == "desenvolvedor" and p.project == "PROD"]
        for p in s.sample(prod_devs, 2):                 # two people of the Produto squad go on vacation in the second sprint
            for d in range(14, 26):
                p.vacation.add(d)
            for d in range(0, 14):
                p.vacation.discard(d)
        candidates = [p for p in self.people if p.role in ("desenvolvedor", "analista de atendimento", "executivo de vendas",
                                                             "analista de qualidade")]
        who = s.choice(candidates)
        who.quits_at = s.randint(9, 22) * MINUTES_PER_DAY + 18 * 60
        opening = board.open_position(0, "atendimento", "analista de atendimento", "SUP", "crescimento")
        for _ in range(2):
            board.candidate(0, opening, "entrevista", s.uniform(0.4, 1.0))
        board.candidate(0, opening, "triagem", s.uniform(0.3, 1.0))
        self.commitments.append({"projeto": "PROD", "prazo": s.randint(24, 26) * MINUTES_PER_DAY + 18 * 60, "pontos": s.randint(46, 58),
                                  "titulo": "integração com o sistema de um cliente grande", "epico": None, "origem": "dono",
                                  "componente": s.choice(SQUAD_COMPONENTS["PROD"])})

    # ======================================================================================================== the day
    def lived_day(self, t, cal):
        """What happens once per lived day: falling sick, resigning, starting a new job, the owner reading the report."""
        for p in self.people:
            if p.active and cal.workday and p.sick_until < t:
                chance = 0.011 * (1.5 if cal.weekday in (0, 4) else 1.0)
                if p.s.random() < chance:
                    p.sick_until = t + p.s.choice((0, 0, 0, 1, 2)) * MINUTES_PER_DAY + MINUTES_PER_DAY - 1
        if cal.workday:
            self._departures_and_notices(t, cal)
            self._hiring(t, cal)
            self._daily_management(t, cal)
            self.escalations_today = 0

    def new_date(self, t, cal):
        """What happens when the calendar date changes: each person's attendance plan, the date's agenda, the squads' rush."""
        board = self.sis["quadro"]
        for p in self.people:
            if not p.active:
                continue
            if p.present and not (p.task and p.task.get("urgente")):
                self._leave(p, t, cal)
            p.date = cal.date
            p.absent = None
            p.overtime_decided = False
            p.overtime_until = 0
            if not cal.workday:
                continue
            if cal.date in p.vacation:
                p.absent = "férias"
                board.log_absence(p.id, p.team, cal.date, "férias")
                continue
            if p.sick_until >= t:
                p.absent = "falta"
                board.log_absence(p.id, p.team, cal.date, "falta")
                continue
            base = cal.date * MINUTES_PER_DAY
            p.arrives_at = base + p.start + p.s.randint(-15, 20)
            shift_len = 540 - (p.friday_early if cal.weekday == 4 else 0)
            p.leaves_at = p.arrives_at + shift_len
            p.lunch_start = base + p.lunch + p.s.randint(-20, 25)
            p.lunch_end = p.lunch_start + p.s.randint(50, 70)
        board.new_day(cal)
        if cal.workday:
            self._daily_agenda(t, cal)
            self._update_haste(cal)

    def _leave(self, p, t, cal):
        p.present = False
        self.sis["quadro"].punch_clock(t, p.id, "saída")
        if p.remote_since is not None:
            minutes = max(1, t - p.remote_since)
            p.remote_since = None
        elif p.overtime_until and p.date == cal.date:
            minutes = max(0, cal.absolute - p.leaves_at)
        else:
            minutes = 0
        if p.date is not None:
            if minutes > 0:
                self.sis["quadro"].log_overtime(p.id, p.team, p.date, minutes)
                p.recent_overtime.append((p.date, minutes))
                del p.recent_overtime[:-15]

    # ======================================================================================================== the minute
    def minute(self, t, cal):
        a = cal.absolute
        agenda = self.sis["agenda"]
        busy = agenda.minute(t, cal)
        before = self.running_before
        if before:
            now_ids = {r[2] for r in agenda.now}
            for r in before:
                if r[2] not in now_ids:
                    action = self.on_end.pop(r[2], None)
                    if action:
                        self._on_meeting_end(t, cal, action, r)
        self.running_before = agenda.now
        self._operations(t, cal)
        if cal.minute % 5 == 0:
            self._development_urgencies(t, cal)
        for p in self.people:
            if not p.active:
                continue
            urgent = p.task is not None and p.task.get("urgente")
            on_shift = p.absent is None and cal.workday and p.date == cal.date and p.arrives_at <= a
            if not p.present:
                if on_shift and a < p.leaves_at:
                    p.present = True
                    p.remote_since = None
                    self.sis["quadro"].punch_clock(t, p.id, "entrada")
                elif urgent:
                    p.present = True                       # called outside working hours: works from home
                    p.remote_since = t
                    self.sis["quadro"].punch_clock(t, p.id, "entrada")
                else:
                    continue
            elif not urgent:
                if p.remote_since is not None or not on_shift:
                    self._leave(p, t, cal)
                    continue
                if a >= max(p.leaves_at, p.overtime_until):
                    if not p.overtime_decided:
                        p.overtime_decided = True
                        extra = self._overtime_minutes(p, t, cal)
                        if extra:
                            p.overtime_until = a + extra
                    if a >= max(p.leaves_at, p.overtime_until):
                        self._leave(p, t, cal)
                        continue
            if p.lunch_start <= a < p.lunch_end and not urgent:
                continue
            if p.id in busy and not urgent:
                continue
            self._work(p, t, cal, a)

    def _work(self, p, t, cal, a):
        cur_task = p.task
        if cur_task is None:
            if p.idle_until > t:
                return
            cur_task = self._choose(p, t, cal)
            if cur_task is None:
                p.idle_until = t + p.s.randint(15, 40)
                return
            p.task = cur_task
        cur_task["resta"] -= 1
        if cur_task["resta"] <= 0:
            p.task = None
            self._finish(p, cur_task, t, cal)
            if p.task is None and p.suspended is not None:
                p.task, p.suspended = p.suspended, None

    def _overtime_minutes(self, p, t, cal):
        """How many minutes the person stays past the end of the day today (0 if they leave)."""
        s = p.s
        cur_task = p.task
        if cur_task is not None and cur_task.get("urgente"):
            return 240
        g = p.group
        if g in ("dev", "qa") and p.project in self.haste:
            pr = self.haste[p.project]
            if pr > 1.12 and s.random() < min(0.85, 0.4 + (pr - 1.0)):
                return s.randint(45, 150)
            if cur_task is not None and cur_task.get("item") and cur_task.get("prioridade") in ("crítica", "alta") and s.random() < 0.5:
                return s.randint(30, 90)
        if g == "atendimento":
            queue = self.sis["fluxo"].count("SUP", "chamado", ("aberto",))
            if queue > 25 and s.random() < 0.6:
                return s.randint(30, 100)
        if g == "vendas" and cal.end_of_month() and s.random() < 0.35:
            return s.randint(30, 75)
        if g == "ops" and (self.incident is not None or self.hotfix):
            return s.randint(60, 180)
        if s.random() < 0.04:
            return s.randint(15, 40)
        return 0

    def _choose(self, p, t, cal):
        inbox = self.sis["porta"]
        if p.group not in ("dono",):
            act = inbox.next_due(p.team, t)
            if act is not None:
                dur = {"pergunta": p.s.randint(10, 25), "pedido": p.s.randint(30, 80), "convocacao": p.s.randint(5, 12)}[act["tipo"]]
                return {"tipo": "ato", "resta": dur, "ato": act["numero"]}
        return getattr(self, CHOOSER[p.group])(p, t, cal)

    def _finish(self, p, cur_task, t, cal):
        getattr(self, FINISHER[cur_task["tipo"]])(p, cur_task, t, cal)

    def _finish_internal(self, p, cur_task, t, cal):
        return None

    def _finish_act(self, p, cur_task, t, cal):
        self.sis["porta"].handle(cur_task["ato"], p, t, cal, self)

    # ======================================================================================================== the agenda
    def _daily_agenda(self, t, cal):
        agenda = self.sis["agenda"]
        if cal.date in agenda.generated:
            return
        agenda.generated.add(cal.date)
        base = cal.date * MINUTES_PER_DAY
        ids = lambda entries: [p.id for p in entries]
        by_team = {e: self.team_members(e) for e in ("produto", "desenvolvimento", "qualidade", "atendimento", "vendas", "operação", "gestão")}
        sq = {pr: [p for p in self.active_people() if p.project == pr and p.group in ("dev", "qa")] for pr in ("PROD", "PLAT")}
        pm = {pr: [p for p in by_team["produto"] if p.project == pr] for pr in ("PROD", "PLAT")}
        agenda.schedule(t, "diária", "atendimento", base + 8 * 60 + 45, 15, ids(by_team["atendimento"]), "diária do atendimento")
        agenda.schedule(t, "diária", "vendas", base + 9 * 60, 15, ids(by_team["vendas"]), "diária de vendas")
        agenda.schedule(t, "diária", "produto", base + 9 * 60 + 15, 15, ids(by_team["produto"]), "diária de produto")
        agenda.schedule(t, "diária", "desenvolvimento", base + 9 * 60 + 30, 15, ids(sq["PROD"] + pm["PROD"][:1]), "diária do squad Produto")
        agenda.schedule(t, "diária", "desenvolvimento", base + 9 * 60 + 45, 15, ids(sq["PLAT"] + pm["PLAT"][:1]), "diária do squad Plataforma")
        agenda.schedule(t, "diária", "operação", base + 10 * 60, 15, ids(by_team["operação"]), "diária da operação")
        if cal.weekday == 0:
            leaders = [p for p in self.active_people() if p.role in ("dono", "líder de produto", "líder técnico", "coordenador de atendimento",
                                                                 "gerente de vendas", "financeiro")] + by_team["operação"][:1]
            agenda.schedule(t, "liderança", "gestão", base + 11 * 60, 60, ids(leaders), "reunião de liderança")
            for e in ("atendimento", "vendas", "operação", "gestão"):
                agenda.schedule(t, "semanal", e, base + 14 * 60 + (30 if e == "gestão" else 0), 60, ids(by_team[e]), f"semanal da equipe de {e}")
        if cal.weekday == 2:
            for pr, hour in (("PROD", 14 * 60), ("PLAT", 15 * 60 + 30)):
                leader = self.leader(pr)
                devs = [p for p in sq[pr] if p.group == "dev" and p is not leader][:2]
                qa = [p for p in sq[pr] if p.group == "qa"][:1]
                agenda.schedule(t, "refinamento", "produto", base + hour, 60, ids(pm[pr] + ([leader] if leader else []) + devs + qa),
                              f"refinamento do squad {pr}")
        if cal.sprint_day == 0:
            for pr, hour, dur in (("PROD", 10 * 60 + 30, 120), ("PLAT", 14 * 60, 120)):
                extra = [p for p in by_team["produto"] if p.role in ("designer", "analista de produto")] if pr == "PROD" else []
                rid = agenda.schedule(t, "planejamento", "desenvolvimento", base + hour, dur, ids(sq[pr] + pm[pr] + extra),
                                    f"planejamento do sprint do squad {pr}")
                self.on_end[rid] = ("planejar", pr)
            rid = agenda.schedule(t, "planejamento", "atendimento", base + 10 * 60 + 15, 30, ids(by_team["atendimento"]), "planejamento do sprint do suporte")
            self.on_end[rid] = ("planejar", "SUP")
            rid = agenda.schedule(t, "planejamento", "operação", base + 10 * 60 + 30, 30, ids(by_team["operação"]), "planejamento do sprint de infraestrutura")
            self.on_end[rid] = ("planejar", "INFRA")
        if cal.sprint_day == 11:
            for pr in ("PROD", "PLAT"):
                rid = agenda.schedule(t, "revisão e retrospectiva", "desenvolvimento", base + 15 * 60, 90, ids(sq[pr] + pm[pr]),
                                    f"revisão e retrospectiva do squad {pr}")
                self.on_end[rid] = ("retrospectiva", pr)
        first_workday = cal.day_of_month == 1 or (cal.weekday == 0 and cal.day_of_month <= 3)
        if first_workday:
            rid = agenda.schedule(t, "mensal", "gestão", base + 16 * 60, 60, ids(self.active_people()), "reunião mensal com a direção")
            self.on_end[rid] = ("mensal", None)

    def _on_meeting_end(self, t, cal, action, r):
        kind, arg = action[0], action[1]
        if kind == "entrevista":
            self._on_interview_end(t, action)
        elif kind == "planejar":
            self._plan_sprint(t, cal, arg)
        elif kind == "retrospectiva":
            sp = self.sis["fluxo"].current_sprint(arg)
            if sp is not None:
                total, done_points, n = self.sis["fluxo"].sprint_points(sp["id"])
                text = (f"entregamos {done_points} de {total} pontos; " + ("faltou gente e sobrou escopo" if done_points < 0.8 * total
                                                                        else "o ritmo ficou bom"))
                self.sis["fluxo"].db.execute("UPDATE sprints SET retrospectiva=? WHERE id=?", (text, sp["id"]))
        elif kind == "mensal":
            if self.commitment_month != cal.month and t - getattr(self, "commitment_t", -10 ** 9) > 20 * MINUTES_PER_DAY:
                self.commitment_month = cal.month
                self.commitment_t = t
                if cal.month > 0 or not self.commitments:
                    # the owner promises the market a launch by the end of the month, sized to what they think the squad can handle
                    s = self.s
                    project = "PROD" if s.random() < 0.7 else "PLAT"
                    sp = self.sis["fluxo"].current_sprint(project)
                    cap = sp["capacidade_pontos"] if sp is not None and sp["capacidade_pontos"] else 40
                    month_end = (cal.date + (cal.days_in_month - cal.day_of_month)) * MINUTES_PER_DAY + 18 * 60
                    self.commitments.append({"projeto": project, "prazo": month_end + s.randint(0, 10) * MINUTES_PER_DAY,
                                              "pontos": int(cap * s.uniform(0.6, 1.4)), "titulo": "lançamento prometido no mês",
                                              "epico": None, "origem": "dono", "componente": s.choice(SQUAD_COMPONENTS[project])})
        elif kind == "pós-incidente":
            workflow = self.sis["fluxo"]
            if not self.runbook:
                workflow.create(t, "INFRA", "tarefa", "escrever o procedimento para volume do banco cheio", priority="alta",
                            component="infra", team="operação", points=2)
            workflow.create(t, "PLAT", "história", "limpeza automática da auditoria do produto", priority="baixa", component="infra",
                        team="desenvolvimento", points=5)

    # ======================================================================================================== sprints
    def _available_days(self, project, cal, days=10):
        devs = [p for p in self.active_people() if p.group == "dev" and p.project == project]
        total = 0
        for p in devs:
            for d in range(cal.date, cal.date + 14):
                if d % 7 < 5 and d not in p.vacation:
                    total += 1
        return total, len(devs)

    def _plan_sprint(self, t, cal, project):
        workflow = self.sis["fluxo"]
        if self.last_planning.get(project, -10 ** 9) > t - 10 * MINUTES_PER_DAY:
            return
        self.last_planning[project] = t
        previous = workflow.current_sprint(project)
        carried_over = []
        if previous is not None:
            total, done_points, n = workflow.sprint_points(previous["id"])
            if project in self.dev_velocity:
                dd = max(1, previous["capacidade_pontos"] / max(0.1, self.dev_velocity[project]))
                measured = done_points / dd if previous["capacidade_pontos"] else self.dev_velocity[project]
                self.dev_velocity[project] = 0.6 * self.dev_velocity[project] + 0.4 * max(0.25, min(1.2, measured))
            workflow.close_sprint(t, previous["id"], previous["retrospectiva"] or "sprint encerrado no planejamento")
            carried_over = [r for r in workflow.items(sprint=previous["id"]) if r["estado"] not in FINAL_STATES and r["estado"] != "pronto para liberar"]
            self.sis["verdade"].sprint_closed(t, project, previous["numero"], total, done_points)
        self.sprint_number[project] += 1
        number = self.sprint_number[project]
        planned_end = (cal.date + 12) * MINUTES_PER_DAY
        if project in ("SUP", "INFRA"):
            sid = workflow.open_sprint(t, project, number, planned_end, 0, 0, "manter a casa em ordem")
            team = "atendimento" if project == "SUP" else "operação"
            points = 0
            for r in carried_over:
                workflow.add_to_sprint(r["id"], sid)
                points += r["pontos"] or 1
            for _ in range(self.s.randint(3, 6)):
                title = (self.s.choice(("artigo na base de conhecimento", "resposta pronta para dúvidas frequentes", "revisão de chamados antigos"))
                          if project == "SUP" else self.s.choice(THEMES["infra"]))
                pts = self.s.choice((1, 2, 2, 3))
                workflow.create(t, project, "tarefa", title, priority="média", component=None if project == "SUP" else "infra",
                            team=team, points=pts, sprint=sid, state="pronto para desenvolver")
                points += pts
            workflow.db.execute("UPDATE sprints SET meta_pontos=?, capacidade_pontos=? WHERE id=?", (points, points, sid))
            self.sis["eventos"].append((t, f"sprint {number} do projeto {'Suporte' if project == 'SUP' else 'Infraestrutura'} aberto"))
            return
        days, ndevs = self._available_days(project, cal)
        capacity = max(8, int(round(days * self.dev_velocity[project])))
        sprint_end = (cal.date + 14) * MINUTES_PER_DAY
        required = []
        for r in carried_over:
            required.append(r)
        # commitments due in this sprint go in whole
        due = [c for c in self.commitments if c["projeto"] == project and c["epico"] is not None and c["prazo"] <= sprint_end + 3 * MINUTES_PER_DAY]
        required_ids = {r["id"] for r in required}
        for c in due:
            for r in workflow.items(project=project, kind="história", extra=f" AND epico={int(c['epico'])} AND estado NOT IN ('liberado', 'pronto para liberar')"):
                if r["id"] not in required_ids:
                    required.append(r)
                    required_ids.add(r["id"])
        for r in workflow.items(project=project, kind="bug", states=("pronto para desenvolver", "triagem", "aberto"),
                             extra=" AND prioridade IN ('alta', 'crítica')"):
            if r["id"] not in required_ids:
                required.append(r)
                required_ids.add(r["id"])
        required_points = sum((r["pontos"] or 2) for r in required)
        goal = max(capacity, required_points)
        chosen = list(required)
        subtotal = required_points
        if subtotal < capacity:
            ready = workflow.items(project=project, kind=("história", "tarefa", "bug"), states=("pronto para desenvolver",),
                                  order_by=PRIO_ORDER_SQL + ", COALESCE(prazo, 1e12), id")
            commitment_ids = {c["epico"] for c in self.commitments if c["epico"] is not None}
            for r in ready:
                if r["id"] in required_ids:
                    continue
                if r["epico"] in commitment_ids:
                    continue                              # what is not due now waits
                pts = r["pontos"] or 2
                if subtotal + pts > capacity:
                    continue
                chosen.append(r)
                subtotal += pts
        sid = workflow.open_sprint(t, project, number, planned_end, goal, capacity, "entregar os compromissos e o épico em andamento")
        for r in chosen:
            workflow.add_to_sprint(r["id"], sid)
            if r["estado"] in ("backlog", "refinamento", "aberto", "triagem"):
                workflow.estimate(r["id"], r["pontos"] or 3)
                workflow.transition(t, r["id"], "pronto para desenvolver", "produto")
        ratio = goal / capacity
        self.planned_load[project] = ratio
        self.haste[project] = max(1.0, ratio)
        self.sis["verdade"].sprint_planned(t, project, number, goal, capacity, ratio, cal)
        self.sis["eventos"].append((t, f"sprint {number} do projeto {'Produto' if project == 'PROD' else 'Plataforma'} aberto com meta de {goal} pontos"))

    def _update_haste(self, cal):
        """Each squad's rush: how much is left in the sprint compared with what can still be done before it ends."""
        workflow = self.sis["fluxo"]
        for project in ("PROD", "PLAT"):
            sp = workflow.current_sprint(project)
            if sp is None:
                self.haste[project] = 1.0
                continue
            total, done_points, n = workflow.sprint_points(sp["id"])
            remaining = total - done_points
            days_left = max(1, 10 - sum(1 for d in range(cal.date - cal.sprint_day, cal.date) if d % 7 < 5))
            devs = [p for p in self.active_people() if p.group == "dev" and p.project == project]
            capacity_left = max(1.0, days_left * len(devs) * self.dev_velocity[project] * 0.9)
            self.haste[project] = max(0.5, min(2.5, remaining / capacity_left))

    # ======================================================================================================== product (the team)
    def _choose_product(self, p, t, cal):
        workflow = self.sis["fluxo"]
        s = p.s
        if p.role == "líder de produto":
            for c in self.commitments:
                if c["epico"] is None:
                    return {"tipo": "epico_compromisso", "resta": s.randint(60, 120), "compromisso": c}
            for project in ("PROD", "PLAT"):
                ep = self.active_epic[project]
                if ep is None or workflow.item(ep)["estado"] == "concluído":
                    return {"tipo": "epico_roteiro", "resta": s.randint(60, 120), "projeto": project}
        projects = (p.project,) if p.project in ("PROD", "PLAT") else ("PROD", "PLAT")
        for project in projects:
            ready = workflow.count(project, "história", ("pronto para desenvolver",)) + workflow.count(project, "tarefa", ("pronto para desenvolver",))
            target = 1.4 * self.dev_velocity[project] * 10 * len([x for x in self.active_people() if x.group == "dev" and x.project == project]) / 3.0
            if ready < target:
                r = workflow.items(project=project, kind="história", states=("refinamento",), order_by=PRIO_ORDER_SQL + ", id", limit=1)
                if r:
                    return {"tipo": "refinar", "resta": s.randint(30, 70), "item": r[0]["id"]}
                r = workflow.items(project=project, kind="história", states=("backlog",), order_by=PRIO_ORDER_SQL + ", id", limit=1)
                if r:
                    return {"tipo": "preparar", "resta": s.randint(20, 45), "item": r[0]["id"]}
                return {"tipo": "historia_avulsa", "resta": s.randint(30, 60), "projeto": project}
        if s.random() < 0.25:
            project = s.choice(projects)
            return {"tipo": "historia_avulsa", "resta": s.randint(30, 60), "projeto": project}
        return {"tipo": "interno", "resta": s.randint(30, 70)}

    def _create_epic(self, t, project, title, n_stories, feature, deadline, component, actor):
        workflow = self.sis["fluxo"]
        s = self.s
        ep = workflow.create(t, project, "épico", title, priority="alta" if deadline else "média", component=component,
                         team="produto", actor=actor, deadline=deadline)
        workflow.transition(t, ep, "em andamento", actor)
        comps = SQUAD_COMPONENTS[project]
        for i in range(n_stories):
            comp = component or s.choice(comps)
            theme = s.choice(THEMES.get(comp, THEMES["catalogo"]))
            pts = s.choice((2, 3, 3, 5, 5, 8))
            h = workflow.create(t, project, "história", f"{title}: {theme}", priority="alta", component=comp,
                            team="desenvolvimento", actor=actor, points=pts, epic=ep, deadline=deadline)
        if feature is not None:
            func_name, impl, route, feat_title = feature
            comp = ROUTE_COMPONENT[route]
            h = workflow.create(t, project, "história", f"{title}: ligar {feat_title}", priority="alta", component=comp,
                            team="desenvolvimento", actor=actor, points=s.choice((3, 5)), epic=ep, deadline=deadline)
            self.feature_story[h] = feature
        return ep

    def _finish_commitment_epic(self, p, cur_task, t, cal):
        c = cur_task["compromisso"]
        if c["epico"] is not None:
            return
        n = max(3, c["pontos"] // 4)
        c["epico"] = self._create_epic(t, c["projeto"], c["titulo"], n, None, c["prazo"], c["componente"], "produto")
        self.sis["fluxo"].comment(t, c["epico"], "produto", "compromisso com prazo; vence no fim do sprint em que cair")

    def _finish_roadmap_epic(self, p, cur_task, t, cal):
        project = cur_task["projeto"]
        workflow = self.sis["fluxo"]
        ep = self.active_epic[project]
        if ep is not None and workflow.item(ep)["estado"] != "concluído":
            return
        func = None
        i = self.next_feature[project]
        for k in range(i, i + 60):
            f = codebase.feature(k)
            comp = ROUTE_COMPONENT[f[2]]
            if COMPONENT_PROJECT[comp] == project:
                func = f
                self.next_feature[project] = k + 1
                break
        title = func[3] if func else "melhorias da plataforma"
        n = self.s.randint(5, 8) if project == "PROD" else self.s.randint(4, 6)
        self.active_epic[project] = self._create_epic(t, project, title, n, func, None, None, "produto")

    def _finish_refine(self, p, cur_task, t, cal):
        workflow = self.sis["fluxo"]
        r = workflow.item(cur_task["item"])
        if r is None or r["estado"] != "refinamento":
            return
        workflow.estimate(r["id"], r["pontos"] or p.s.choice((2, 3, 5)))
        workflow.transition(t, r["id"], "pronto para desenvolver", "produto")
        if p.s.random() < 0.4:
            workflow.comment(t, r["id"], "produto", "critérios de aceite revisados")

    def _finish_prepare(self, p, cur_task, t, cal):
        workflow = self.sis["fluxo"]
        r = workflow.item(cur_task["item"])
        if r is not None and r["estado"] == "backlog":
            workflow.transition(t, r["id"], "refinamento", "produto")

    def _finish_standalone_story(self, p, cur_task, t, cal):
        project = cur_task["projeto"]
        s = p.s
        comp = s.choice(SQUAD_COMPONENTS[project])
        kind = "história" if s.random() < 0.7 else "tarefa"
        self.sis["fluxo"].create(t, project, kind, s.choice(THEMES[comp]), priority=s.choice(("baixa", "média", "média", "alta")),
                                component=comp, team="desenvolvimento", actor="produto", points=s.choice((1, 2, 3, 5)))

    # ======================================================================================================== development
    def _choose_dev(self, p, t, cal):
        workflow = self.sis["fluxo"]
        s = p.s
        pr = p.project
        # 1. what came back to me (review or quality asked for a fix)
        for r in workflow.items(project=pr, states=("em desenvolvimento", "em andamento"), assignee=p.id, limit=3):
            if r["id"] in self.rejections:
                return {"tipo": "corrigir", "resta": s.randint(30, 110) / p.speed, "item": r["id"], "prioridade": r["prioridade"]}
        # 2. urgent bugs do not wait for triage
        r = workflow.items(project=pr, kind="bug", states=("aberto", "triagem", "pronto para desenvolver"), assignee=None,
                        extra=" AND prioridade IN ('crítica', 'alta')", order_by=PRIO_ORDER_SQL + ", id", limit=1)
        if r:
            return self._take(p, t, r[0], "investigar", s.randint(30, 140) / p.speed)
        # 3. triage (tech lead)
        if p.role == "líder técnico":
            r = workflow.items(project=pr, kind="bug", states=("aberto",), order_by="id", limit=1)
            if r:
                return {"tipo": "triagem", "resta": s.randint(10, 25), "item": r[0]["id"]}
        # 4. review colleagues' code
        r = workflow.items(project=pr, states=("em revisão",), extra=f" AND (responsavel IS NULL OR responsavel<>{p.id})",
                        order_by="atualizado_em", limit=4)
        for item in r:
            if item["id"] not in self.rejections and self.author.get(item["id"]) != p.id and not item["id"] in self._under_review():
                return {"tipo": "revisar", "resta": s.randint(15, 45), "item": item["id"]}
        # 5. continue my own work
        for r in workflow.items(project=pr, states=("em desenvolvimento", "em andamento"), assignee=p.id, limit=3):
            if r["id"] in self.remaining:
                block = min(self.remaining[r["id"]], s.randint(120, 300))
                return {"tipo": "desenvolver", "resta": block, "bloco": block, "item": r["id"], "prioridade": r["prioridade"]}
        # 6. the next sprint item
        sp = workflow.current_sprint(pr)
        if sp is not None:
            cands = workflow.items(project=pr, states=("pronto para desenvolver",), sprint=sp["id"], assignee=None,
                                order_by=PRIO_ORDER_SQL + ", COALESCE(prazo, 1e12), id", limit=8)
            for r in cands:
                if r["id"] in self.feature_story and not self._epic_ready_to_enable(r):
                    continue
                if r["tipo"] == "bug":
                    return self._take(p, t, r, "investigar", s.randint(30, 140) / p.speed)
                return self._take(p, t, r, "desenvolver", self._duration(p, r))
        # 7. unplanned: pull from what is ready (a commitment that is not due yet waits)
        cands = workflow.items(project=pr, kind=("história", "tarefa", "bug"), states=("pronto para desenvolver",), assignee=None,
                            order_by=PRIO_ORDER_SQL + ", id", limit=12)
        deferred_epics = {c["epico"] for c in self.commitments if c["epico"] is not None}
        for r in cands:
            if r["id"] in self.feature_story and not self._epic_ready_to_enable(r):
                continue
            if r["epico"] in deferred_epics and r["sprint"] is None:
                continue
            if sp is not None:
                workflow.add_to_sprint(r["id"], sp["id"])
            if r["tipo"] == "bug":
                return self._take(p, t, r, "investigar", s.randint(30, 140) / p.speed)
            return self._take(p, t, r, "desenvolver", self._duration(p, r))
        return {"tipo": "interno", "resta": s.randint(25, 60)}

    def _under_review(self):
        out = set()
        for q in self.people:
            if q.task is not None and q.task["tipo"] == "revisar":
                out.add(q.task["item"])
        return out

    def _epic_ready_to_enable(self, r):
        workflow = self.sis["fluxo"]
        others = workflow.db.execute("SELECT COUNT(*) FROM itens WHERE epico=? AND id<>? AND estado NOT IN ('liberado', 'pronto para liberar')",
                                  (r["epico"], r["id"])).fetchone()[0]
        return others == 0

    def _duration(self, p, r):
        pts = r["pontos"] or 2
        rush = max(0.0, min(1.0, self.haste.get(p.project, 1.0) - 1.0))
        return pts * MINUTES_PER_POINT / p.speed * (1.0 - 0.22 * rush) * p.s.lognormvariate(0.0, 0.3)

    def _take(self, p, t, r, kind, dur):
        workflow = self.sis["fluxo"]
        dst = "em andamento" if r["tipo"] == "tarefa" else "em desenvolvimento"
        if r["tipo"] == "bug" and r["estado"] == "triagem":
            workflow.transition(t, r["id"], "pronto para desenvolver", "desenvolvimento")
        workflow.transition(t, r["id"], dst, "desenvolvimento", team="desenvolvimento")
        workflow.assign_to(r["id"], p.id)
        self.author[r["id"]] = p.id
        if p.s.random() < 0.3:
            workflow.comment(t, r["id"], "desenvolvimento", "comecei; dúvida sobre o comportamento esperado registrada")
        if kind == "desenvolver":
            self.remaining[r["id"]] = dur
            dur = min(dur, p.s.randint(120, 300))
        cur_task = {"tipo": kind, "resta": dur, "bloco": dur, "item": r["id"], "prioridade": r["prioridade"]}
        if r["prioridade"] == "crítica":
            cur_task["urgente"] = True
        return cur_task

    def _finish_triage(self, p, cur_task, t, cal):
        workflow = self.sis["fluxo"]
        r = workflow.item(cur_task["item"])
        if r is None or r["estado"] != "aberto":
            return
        workflow.transition(t, r["id"], "triagem", "desenvolvimento")
        tickets = len(workflow.links_to(r["id"], "escalado para"))
        prio = r["prioridade"]
        if tickets >= 6 or r["origem"] == "monitoramento":
            prio = "crítica"
        elif tickets >= 2 and prio in ("baixa", "média"):
            prio = "alta"
        if prio != r["prioridade"]:
            workflow.set_priority(r["id"], prio)
        workflow.estimate(r["id"], p.s.choice((1, 2, 2, 3)))
        if prio in ("alta", "crítica"):
            sp = workflow.current_sprint(r["projeto"])
            if sp is not None:
                workflow.add_to_sprint(r["id"], sp["id"])
        workflow.transition(t, r["id"], "pronto para desenvolver", "desenvolvimento")
        workflow.comment(t, r["id"], "desenvolvimento", f"triagem: prioridade {prio}")

    def _finish_develop(self, p, cur_task, t, cal):
        workflow = self.sis["fluxo"]
        repo = self.sis["repo"]
        r = workflow.item(cur_task["item"])
        if r is None or r["estado"] not in ("em desenvolvimento", "em andamento"):
            self.remaining.pop(cur_task["item"], None)
            return
        missing = self.remaining.get(r["id"], 0) - cur_task.get("bloco", 0)
        if missing > 1:
            self.remaining[r["id"]] = missing
            if p.s.random() < 0.35:
                repo.commit(t, r["id"], r["componente"], {}, p.s.randint(10, 120), "desenvolvimento", "trabalho em andamento")
            if p.s.random() < 0.12:
                workflow.comment(t, r["id"], "desenvolvimento", "andamento registrado")
            return
        self.remaining.pop(r["id"], None)
        changes = {}
        func = self.feature_story.get(r["id"])
        if func is not None:
            changes[func[0]] = func[1]
        comp = r["componente"]
        pts = r["pontos"] or 2
        rush = max(0.0, self.haste.get(p.project, 1.0) - 1.0)
        chance = 1.0 - math.exp(-0.05 * pts * (1.0 + 2.0 * min(1.0, rush)) * p.sloppiness)
        if comp in SQUAD_COMPONENTS.get(r["projeto"], ()) or comp == "login":
            if p.s.random() < chance:
                branch = repo.branch_code(r["id"])
                branch.update(changes)
                options = [(f, v) for (f, v) in codebase.DEFECTS if codebase.FUNCTION_COMPONENT[f] == comp
                          and branch[f] == repo.sound[f] and f not in changes]
                if options:
                    f, v = p.s.choice(sorted(options))
                    changes[f] = v
                    self.sis["verdade"].defect_written(t, r["id"], r["projeto"], f, v, self.haste.get(p.project, 1.0))
        rows = int(pts * p.s.randint(25, 90))
        repo.commit(t, r["id"], comp, changes, rows, "desenvolvimento", r["titulo"])
        if p.s.random() < 0.5:
            repo.commit(t, r["id"], comp, {}, int(rows * 0.3), "desenvolvimento", "ajustes")
        workflow.transition(t, r["id"], "em revisão", "desenvolvimento")
        workflow.comment(t, r["id"], "desenvolvimento", "pronto para revisão")

    def _finish_fix(self, p, cur_task, t, cal):
        workflow = self.sis["fluxo"]
        repo = self.sis["repo"]
        r = workflow.item(cur_task["item"])
        functions = self.rejections.pop(cur_task["item"], [])
        if r is None:
            return
        changes = {f: repo.sound[f] for f in functions}
        repo.commit(t, r["id"], r["componente"], changes, p.s.randint(5, 60), "desenvolvimento", "correção do que voltou")
        dest = "em qualidade" if r["tipo"] in ("história", "bug") else "em revisão"
        workflow.transition(t, r["id"], dest, "desenvolvimento", team="qualidade" if dest == "em qualidade" else None)
        if dest == "em qualidade":
            workflow.assign_to(r["id"], None)
        workflow.comment(t, r["id"], "desenvolvimento", "corrigido; pode testar de novo")

    def _finish_review(self, p, cur_task, t, cal):
        workflow = self.sis["fluxo"]
        repo = self.sis["repo"]
        r = workflow.item(cur_task["item"])
        if r is None or r["estado"] != "em revisão":
            return
        branch = repo.branches.get(r["id"], {})
        defects = [f for f, v in branch.items() if (f, v) in codebase.DEFECTS]
        rush = max(0.0, min(1.0, self.haste.get(p.project, 1.0) - 1.0))
        if defects and p.s.random() < 0.3 * (1.0 - 0.5 * rush):
            repo.record_review(t, r["id"], "pediu mudanças")
            self.rejections[r["id"]] = defects
            workflow.transition(t, r["id"], "em andamento" if r["tipo"] == "tarefa" else "em desenvolvimento", "desenvolvimento")
            workflow.assign_to(r["id"], self.author.get(r["id"]))
            workflow.comment(t, r["id"], "desenvolvimento", "revisão: a mudança quebra um caso; ver comentário no código")
            for f in defects:
                self.sis["verdade"].defect_blocked(t, r["id"], f, "revisão de código")
            return
        if r["tipo"] == "tarefa" and self.null == "sem_defeito" and r["componente"]:
            # in the "sem_defeito" null variant nothing reaches main without the full test suite
            n, failures = run_tests(repo.branch_code(r["id"]), r["componente"], p.s, 1.0, run_all=True)
            repo.record_tests(t, r["componente"], "ramo", n, len(failures), "desenvolvimento")
            if failures:
                self.rejections[r["id"]] = sorted({f for f, _, _ in failures})
                workflow.transition(t, r["id"], "em andamento", "desenvolvimento")
                workflow.assign_to(r["id"], self.author.get(r["id"]))
                return
        repo.record_review(t, r["id"], "aprovou")
        if r["tipo"] == "tarefa":
            workflow.transition(t, r["id"], "pronto para liberar", "desenvolvimento")
            repo.merge(r["id"])
        else:
            workflow.transition(t, r["id"], "em qualidade", "desenvolvimento", team="qualidade")
            workflow.assign_to(r["id"], None)

    def _finish_investigate(self, p, cur_task, t, cal):
        """A bug: reproduce (run the component's full suite against the live code and main), fix or close."""
        workflow = self.sis["fluxo"]
        repo = self.sis["repo"]
        r = workflow.item(cur_task["item"])
        if r is None or r["estado"] not in ("em desenvolvimento",):
            return
        comp = r["componente"]
        if comp is None or comp == "infra":
            workflow.transition(t, r["id"], "não reproduzido", "desenvolvimento")
            workflow.comment(t, r["id"], "desenvolvimento", "não é do código do produto")
            return
        live = repo.versions[repo.live]
        n1, failures_live = run_tests(live, comp, p.s, 1.0, run_all=True)
        n2, failures_main = run_tests(repo.main_branch, comp, p.s, 1.0, run_all=True)
        repo.record_tests(t, comp, "no ar", n1, len(failures_live), "desenvolvimento")
        repo.record_tests(t, comp, "principal", n2, len(failures_main), "desenvolvimento")
        functions = sorted({f for f, _, _ in failures_live} | {f for f, _, _ in failures_main})
        if not functions:
            workflow.transition(t, r["id"], "não reproduzido", "desenvolvimento")
            workflow.comment(t, r["id"], "desenvolvimento", "não reproduzimos; testes do componente passam")
            return
        changes = {f: repo.sound[f] for f in functions}
        repo.commit(t, r["id"], comp, changes, p.s.randint(5, 40), "desenvolvimento", f"correção em {', '.join(functions)}")
        self.hotfix_functions = getattr(self, "hotfix_functions", {})
        self.hotfix_functions[r["id"]] = changes
        in_main = {f for f, _, _ in failures_main}
        for f in functions:
            origin = repo.authorship.get(f) if f in in_main else None
            if origin is not None and origin != r["id"]:
                o = workflow.item(origin)
                if o is not None and o["estado"] == "liberado" and o["tipo"] in ("história", "tarefa"):
                    workflow.transition(t, origin, "em desenvolvimento" if o["tipo"] != "tarefa" else "em andamento", "desenvolvimento")
                    workflow.connect(t, r["id"], origin, "causado por")
                    workflow.comment(t, origin, "desenvolvimento", "reaberto: um bug no ar veio desta mudança")
        workflow.comment(t, r["id"], "desenvolvimento", "reproduzido nos testes; correção pronta")
        workflow.transition(t, r["id"], "em qualidade", "desenvolvimento", team="qualidade")
        workflow.assign_to(r["id"], None)

    # ======================================================================================================== quality
    def _choose_qa(self, p, t, cal):
        workflow = self.sis["fluxo"]
        s = p.s
        pr = p.project
        r = workflow.items(project=pr, states=("em qualidade",), assignee=None, order_by=PRIO_ORDER_SQL + ", atualizado_em", limit=1)
        if r:
            r = r[0]
            workflow.assign_to(r["id"], p.id)
            if r["tipo"] == "bug":
                dur = s.randint(20, 45)
            else:
                rush = max(0.0, min(1.0, self.haste.get(pr, 1.0) - 1.0))
                dur = (r["pontos"] or 2) * s.randint(35, 70) * (1.0 - 0.35 * rush) + 20
            return {"tipo": "testar", "resta": dur, "item": r["id"], "prioridade": r["prioridade"]}
        if cal.weekday in (1, 3) and 9 * 60 + 30 <= cal.minute < 12 * 60 and self.last_regression.get(pr, -10 ** 9) < t - 36 * 60:
            self.last_regression[pr] = t
            return {"tipo": "regressao", "resta": s.randint(40, 90)}
        if s.random() < 0.3:
            return {"tipo": "interno", "resta": s.randint(30, 60)}
        return None

    def _finish_test(self, p, cur_task, t, cal):
        workflow = self.sis["fluxo"]
        repo = self.sis["repo"]
        r = workflow.item(cur_task["item"])
        if r is None or r["estado"] != "em qualidade":
            return
        comp = r["componente"]
        rush = max(0.0, min(1.0, self.haste.get(p.project, 1.0) - 1.0))
        run_all = r["tipo"] == "bug" or self.null == "sem_defeito"
        coverage = p.coverage * (1.0 - 0.5 * rush)
        cod = repo.branch_code(r["id"])
        n, failures = run_tests(cod, comp, p.s, coverage, run_all=run_all) if comp else (0, [])
        repo.record_tests(t, comp or "", "ramo", n, len(failures), "qualidade")
        if failures:
            functions = sorted({f for f, _, _ in failures})
            self.rejections[r["id"]] = functions
            workflow.transition(t, r["id"], "em desenvolvimento", "qualidade", team="desenvolvimento")
            workflow.assign_to(r["id"], self.author.get(r["id"]))
            workflow.comment(t, r["id"], "qualidade", "reprovado: " + "; ".join(name for _, name, _ in failures))
            for f in functions:
                self.sis["verdade"].defect_blocked(t, r["id"], f, "qualidade")
            return
        workflow.transition(t, r["id"], "pronto para liberar", "qualidade")
        workflow.comment(t, r["id"], "qualidade", f"aprovado; {n} testes")
        repo.merge(r["id"])
        if r["tipo"] == "bug" and r["prioridade"] in ("crítica", "alta"):
            self.hotfix.append(r["id"])

    def _finish_regression(self, p, cur_task, t, cal):
        """Before the release: some components of main, with a partial suite."""
        repo = self.sis["repo"]
        workflow = self.sis["fluxo"]
        comps = SQUAD_COMPONENTS[p.project]
        for comp in p.s.sample(list(comps), 2):
            n, failures = run_tests(repo.main_branch, comp, p.s, 0.4)
            repo.record_tests(t, comp, "principal", n, len(failures), "qualidade")
            for func_name in sorted({f for f, _, _ in failures}):
                origin = repo.authorship.get(func_name)
                bug = workflow.create(t, p.project, "bug", f"regressão em {COMPONENT_NAME[comp]}", priority="alta", component=comp,
                                  team="desenvolvimento", actor="qualidade", origin="qualidade")
                if origin is not None:
                    workflow.connect(t, bug, origin, "causado por")
                    o = workflow.item(origin)
                    if o is not None and o["estado"] == "liberado" and o["tipo"] in ("história", "tarefa"):
                        workflow.transition(t, origin, "em desenvolvimento" if o["tipo"] != "tarefa" else "em andamento", "qualidade")
                self.sis["verdade"].defect_blocked(t, origin, func_name, "regressão")

    # ======================================================================================================== support
    def _choose_support(self, p, t, cal):
        workflow = self.sis["fluxo"]
        s = p.s
        # escalated tickets whose target is already resolved
        r = workflow.db.execute(
            "SELECT c.id FROM itens c JOIN ligacoes l ON l.de = c.id AND l.tipo='escalado para' JOIN itens b ON b.id = l.para "
            "WHERE c.projeto='SUP' AND c.estado='escalado' AND b.estado IN ('liberado', 'não reproduzido', 'concluído') "
            "ORDER BY c.id LIMIT 1").fetchone()
        if r is not None:
            return {"tipo": "resolver_escalado", "resta": s.randint(4, 10), "item": r[0]}
        focus, until = self.support_focus
        cond = ""
        if focus and t < until:
            cond = f"CASE WHEN componente='{focus}' THEN 0 ELSE 1 END, "
        r = workflow.db.execute(
            "SELECT * FROM itens WHERE projeto='SUP' AND tipo='chamado' AND COALESCE(origem, '') <> 'porta' AND (estado='aberto' OR "
            "(estado='em atendimento' AND responsavel IS NULL)) ORDER BY " + cond + "criado_em + CASE prioridade WHEN 'crítica' THEN 60 WHEN 'alta' THEN 240 "
            "WHEN 'média' THEN 1440 ELSE 4320 END, id LIMIT 1").fetchone()
        if r is not None:
            workflow.assign_to(r["id"], p.id)
            if r["estado"] == "aberto":
                workflow.transition(t, r["id"], "em atendimento", "atendimento")
            mass_incident = self.incident is not None or (self.sis["clientes"].tickets.get(r["id"], {}).get("motivo") == "erro"
                                                  and workflow.count("SUP", "chamado", ("aberto",)) > 30)
            dur = s.randint(5, 12) if mass_incident else s.lognormvariate(math.log(20), 0.45)
            return {"tipo": "chamado", "resta": dur, "item": r["id"]}
        sp = workflow.current_sprint("SUP")
        if sp is not None and s.random() < 0.5:
            r = workflow.items(project="SUP", kind="tarefa", states=("pronto para desenvolver",), sprint=sp["id"], assignee=None, limit=1)
            if r:
                workflow.transition(t, r[0]["id"], "em andamento", "atendimento")
                workflow.assign_to(r[0]["id"], p.id)
                return {"tipo": "tarefa_simples", "resta": (r[0]["pontos"] or 1) * s.randint(90, 180), "item": r[0]["id"]}
        return {"tipo": "interno", "resta": s.randint(10, 30)}

    def _finish_ticket(self, p, cur_task, t, cal):
        workflow = self.sis["fluxo"]
        cust = self.sis["clientes"]
        r = workflow.item(cur_task["item"])
        if r is None or r["estado"] != "em atendimento":
            return
        d = cust.tickets.get(r["id"], {})
        reason = d.get("motivo", "dúvida")
        s = p.s
        comp = r["componente"]
        if reason == "cancelamento":
            self.sis["quadro"].request(t, "cancelamento", "cliente pediu cancelamento", customer=r["cliente"])
            workflow.comment(t, r["id"], "atendimento", "encaminhado ao financeiro")
            self._resolve(t, r["id"])
            return
        if reason in ("dúvida", "fatura"):
            if s.random() < 0.8 or "o cliente respondeu" in self._last_comments(r["id"]):
                workflow.comment(t, r["id"], "atendimento", "orientação enviada")
                self._resolve(t, r["id"])
            else:
                workflow.comment(t, r["id"], "atendimento", "pedimos mais detalhes")
                workflow.transition(t, r["id"], "aguardando cliente", "atendimento")
                cust.ask_customer(t, r["id"], cal)
            return
        # technical problem: open incident, known bug, or escalate
        if self.incident is not None and self.incident.get("item") is not None:
            self._escalate(t, r, self.incident["item"], "incidente em andamento")
            return
        if reason == "cobrança em dobro" and s.random() < 0.7:
            self.sis["quadro"].request(t, "estorno", "estornar cobrança em dobro", customer=r["cliente"])
        known = workflow.db.execute(
            "SELECT id FROM itens WHERE tipo='bug' AND componente=? AND estado NOT IN ('liberado', 'não reproduzido') AND criado_em > ? "
            "ORDER BY id DESC LIMIT 1", (comp, t - 5 * MINUTES_PER_DAY)).fetchone()
        if known is not None:
            self._escalate(t, r, known[0], "mesmo problema de um bug aberto")
            n = len(workflow.links_to(known[0], "escalado para"))
            b = workflow.item(known[0])
            updated = "crítica" if n >= 6 else ("alta" if n >= 3 else None)
            if updated and b is not None and PRIO_RANK[updated] < PRIO_RANK[b["prioridade"]]:
                workflow.set_priority(known[0], updated)
                workflow.comment(t, known[0], "atendimento", f"já são {n} chamados ligados a este bug")
            return
        if s.random() < 0.25 and "o cliente respondeu" not in self._last_comments(r["id"]):
            workflow.comment(t, r["id"], "atendimento", "pedimos passos para reproduzir")
            workflow.transition(t, r["id"], "aguardando cliente", "atendimento")
            cust.ask_customer(t, r["id"], cal)
            return
        recent = workflow.db.execute("SELECT COUNT(*) FROM itens WHERE projeto='SUP' AND componente=? AND criado_em > ? AND tipo='chamado'",
                                    (comp, t - 180)).fetchone()[0]
        prio = "crítica" if recent >= 8 else ("alta" if recent >= 3 or r["prioridade"] in ("alta", "crítica") else "média")
        project = COMPONENT_PROJECT.get(comp, "PROD")
        if project == "INFRA":
            project = "PLAT"
        title = {"erro": f"erro em {COMPONENT_NAME.get(comp, comp)} relatado por clientes",
                  "lentidão": f"lentidão em {COMPONENT_NAME.get(comp, comp)}", "cobrança em dobro": "cliente cobrado duas vezes",
                  "nota não emitida": "nota fiscal não emitida"}.get(reason, "problema relatado por cliente")
        bug = workflow.create(t, project, "bug", title, priority=prio, component=comp, team="desenvolvimento", actor="atendimento",
                          origin="atendimento")
        self._escalate(t, r, bug, "escalado para o desenvolvimento")

    def _last_comments(self, item):
        return " ".join(x[0] for x in self.sis["fluxo"].db.execute("SELECT texto FROM comentarios WHERE item=? ORDER BY id DESC LIMIT 3", (item,)).fetchall())

    def _escalate(self, t, r, dest, text):
        workflow = self.sis["fluxo"]
        workflow.connect(t, r["id"], dest, "escalado para")
        workflow.comment(t, r["id"], "atendimento", text)
        workflow.transition(t, r["id"], "escalado", "atendimento")
        self.escalations_today += 1
        self.sis["verdade"].escalated(t, r["id"], dest)

    def _resolve(self, t, item):
        workflow = self.sis["fluxo"]
        workflow.transition(t, item, "resolvido", "atendimento")
        self.sis["clientes"].ticket_resolved(t, item)

    def _finish_resolve_escalated(self, p, cur_task, t, cal):
        workflow = self.sis["fluxo"]
        r = workflow.item(cur_task["item"])
        if r is None or r["estado"] != "escalado":
            return
        workflow.transition(t, r["id"], "em atendimento", "atendimento")
        workflow.comment(t, r["id"], "atendimento", "o problema foi corrigido; avisamos o cliente")
        self._resolve(t, r["id"])

    def _finish_simple_task(self, p, cur_task, t, cal):
        workflow = self.sis["fluxo"]
        r = workflow.item(cur_task["item"])
        if r is not None and r["estado"] == "em andamento":
            workflow.transition(t, r["id"], "concluído", p.team)

    # ======================================================================================================== sales
    def _choose_sdr(self, p, t, cal):
        crm = self.sis["crm"]
        s = p.s
        n = crm.next_due(t, ("lead",))
        if n is not None:
            crm.assign(n["id"], p.id)
            return {"tipo": "ligar_lead", "resta": s.randint(12, 30), "negocio": n["id"]}
        if crm.count_in_stage("lead") < 3 and s.random() < 0.22:
            return {"tipo": "prospectar", "resta": s.randint(35, 70)}
        return {"tipo": "interno", "resta": s.randint(20, 45)}

    def _finish_call_lead(self, p, cur_task, t, cal):
        crm = self.sis["crm"]
        n = crm.deal(cur_task["negocio"])
        if n is None or n[2] != "lead":
            return
        s = p.s
        crm.log_activity(t, n[0], "ligação")
        r = s.random()
        if r < 0.35:
            owner = self._least_loaded_executive(crm)
            crm.move(t, n[0], "qualificação", next_at=t)
            if owner is not None:
                crm.assign(n[0], owner.id)
        elif r < 0.65:
            crm.move(t, n[0], "perdido")
        else:
            if n[8] >= 2:
                crm.move(t, n[0], "perdido")
            else:
                crm.postpone(t, n[0], t + MINUTES_PER_DAY)

    def _least_loaded_executive(self, crm):
        execs = [p for p in self.active_people() if p.role == "executivo de vendas"]
        if not execs:
            return None
        workloads = []
        for p in execs:
            c = crm.db.execute("SELECT COUNT(*) FROM negocios WHERE responsavel=? AND estagio IN ('qualificação', 'proposta', 'negociação')",
                               (p.id,)).fetchone()[0]
            workloads.append((c, p.id, p))
        return min(workloads)[2]

    def _finish_prospect(self, p, cur_task, t, cal):
        s = p.s
        crm = self.sis["crm"]
        for _ in range(s.choice((0, 1, 1, 2))):
            plan = s.choice(("básico", "básico", "pro", "empresarial"))
            crm.new_deal(t, "prospecção", plan, PLAN_VALUE[plan], next_at=t + s.randint(30, 240))
        crm.log_activity(t, None, "e-mail")

    def _choose_sales(self, p, t, cal):
        crm = self.sis["crm"]
        s = p.s
        n = crm.next_due(t, ("qualificação", "proposta", "negociação"), assignee=p.id)
        if n is not None:
            crm.assign(n["id"] if hasattr(n, "keys") else n[0], p.id)
            cur_stage = n[2]
            dur = {"qualificação": s.randint(15, 30), "proposta": s.randint(15, 30), "negociação": s.randint(20, 40)}[cur_stage]
            if cur_stage == "qualificação" and n[8] == 1:
                dur = s.randint(40, 80)                      # write the proposal after the demo
            return {"tipo": "negocio", "resta": dur, "negocio": n[0]}
        if p.role == "gerente de vendas" and s.random() < 0.3:
            return {"tipo": "interno", "resta": s.randint(30, 60)}
        if (cal.end_of_month() and s.random() < 0.35) or t < self.sales_focus:
            n = crm.db.execute("SELECT id FROM negocios WHERE estagio IN ('proposta', 'negociação') AND responsavel=? ORDER BY proxima_acao_em LIMIT 1",
                               (p.id,)).fetchone()
            if n is not None:
                crm.db.execute("UPDATE negocios SET proxima_acao_em=? WHERE id=?", (t, n[0]))
                return {"tipo": "negocio", "resta": s.randint(15, 30), "negocio": n[0]}
        if crm.count_in_stage("qualificação") + crm.count_in_stage("proposta") < 5 and s.random() < 0.15:
            return {"tipo": "prospectar", "resta": s.randint(35, 70)}
        return {"tipo": "interno", "resta": s.randint(20, 50)}

    def _finish_deal(self, p, cur_task, t, cal):
        crm = self.sis["crm"]
        n = crm.deal(cur_task["negocio"])
        if n is None or n[2] not in ("qualificação", "proposta", "negociação"):
            return
        s = p.s
        a = cal.absolute
        cur_stage = n[2]
        if cur_stage == "qualificação":
            if n[8] == 0:                                   # schedule the demo
                people = [p.id]
                if n[3] == "empresarial":
                    g = [x for x in self.active_people() if x.role == "gerente de vendas"]
                    people += [x.id for x in g[:1]]
                begin = self.sis["agenda"].first_free_slot(people, a + s.randint(1, 3) * MINUTES_PER_DAY - 6 * 60, 60)
                if begin is None:
                    crm.postpone(t, n[0], t + MINUTES_PER_DAY)
                    return
                self.sis["agenda"].schedule(t, "com cliente", "vendas", begin, s.choice((45, 60)), people, "demonstração para um lead")
                crm.log_activity(t, n[0], "e-mail")
                crm.db.execute("UPDATE negocios SET proxima_acao_em=?, tentativas=1 WHERE id=?", (t + (begin - a) + 60, n[0]))
                return
            crm.log_activity(t, n[0], "proposta")
            crm.move(t, n[0], "proposta", next_at=t + s.randint(2, 4) * MINUTES_PER_DAY)
            return
        crm.log_activity(t, n[0], "ligação")
        month_end = cal.end_of_month()
        if cur_stage == "proposta":
            r = s.random()
            if r < 0.42:
                crm.move(t, n[0], "negociação", next_at=t + s.randint(1, 3) * MINUTES_PER_DAY)
            elif r < 0.58:
                crm.move(t, n[0], "perdido")
            else:
                crm.postpone(t, n[0], t + s.randint(2, 4) * MINUTES_PER_DAY)
            return
        won = 0.135 * (1.6 if month_end else 1.0)
        r = s.random()
        if r < won:
            crm.move(t, n[0], "ganho")
            plan = n[3]
            self.sis["quadro"].request(t, "nova conta", f"criar conta do plano {plan}", customer=n[0])
            if plan == "empresarial" and s.random() < 0.55:
                project = "PROD" if s.random() < 0.7 else "PLAT"
                self.commitments.append({"projeto": project, "prazo": t + s.randint(21, 35) * MINUTES_PER_DAY, "pontos": s.randint(18, 40),
                                          "titulo": "funcionalidade prometida a um cliente empresarial", "epico": None,
                                          "origem": "vendas", "componente": s.choice(SQUAD_COMPONENTS[project])})
        elif r < won + 0.12:
            crm.move(t, n[0], "perdido")
        else:
            crm.postpone(t, n[0], t + (MINUTES_PER_DAY if month_end else s.randint(1, 3) * MINUTES_PER_DAY))

    # ======================================================================================================== management
    def _choose_finance(self, p, t, cal):
        q = self.sis["quadro"]
        s = p.s
        r = q.next_request(t, ("nova conta", "cancelamento", "estorno"))
        if r is not None:
            q.db.execute("UPDATE solicitacoes SET estado='em andamento' WHERE id=?", (r[0],))
            return {"tipo": "solicitacao", "resta": s.randint(20, 50), "sid": r[0], "stipo": r[2], "cliente": r[6]}
        return {"tipo": "interno", "resta": s.randint(30, 70)}

    def _finish_request(self, p, cur_task, t, cal):
        q = self.sis["quadro"]
        cust = self.sis["clientes"]
        if cur_task["stipo"] == "nova conta":
            n = self.sis["crm"].deal(cur_task["cliente"])
            plan = n[3] if n is not None else "básico"
            c = cust.join(t, plan, self.sis["produto"], self.sis["verdade"])
            onboarding = [x.id for x in self.active_people() if x.role == "analista de atendimento"]
            if onboarding:
                who = [p.s.choice(onboarding)]
                begin = self.sis["agenda"].first_free_slot(who, cal.absolute, 45)
                if begin is not None:
                    self.sis["agenda"].schedule(t, "com cliente", "atendimento", begin, 45, who, "boas-vindas a um cliente novo")
        elif cur_task["stipo"] == "cancelamento":
            cust.churn(t, cur_task["cliente"], self.sis["produto"], self.sis["verdade"])
        elif cur_task["stipo"] == "estorno":
            self.sis["estornos"][0] += 1
        q.complete_request(t, cur_task["sid"])

    def _choose_hr(self, p, t, cal):
        q = self.sis["quadro"]
        s = p.s
        for v in q.active_openings():
            if v[6] != "aberta":
                continue
            if q.candidates(v[0], "proposta"):
                return {"tipo": "fechar_vaga", "resta": s.randint(20, 40), "vaga": v[0]}
            if q.candidates(v[0], "entrevista") and not self._interview_scheduled(v[0]):
                return {"tipo": "marcar_entrevista", "resta": s.randint(10, 20), "vaga": v[0]}
            if q.candidates(v[0], "triagem"):
                return {"tipo": "triar", "resta": s.randint(20, 40), "vaga": v[0]}
            if s.random() < 0.3:
                return {"tipo": "buscar_candidatos", "resta": s.randint(40, 90), "vaga": v[0]}
        return self._choose_finance(p, t, cal)

    def _interview_scheduled(self, opening):
        return any(k[0] == "entrevista" and k[1] == opening for k in self.on_end.values())

    def _finish_source_candidates(self, p, cur_task, t, cal):
        for _ in range(p.s.randint(1, 3)):
            self.sis["quadro"].candidate(t, cur_task["vaga"], "triagem", p.s.uniform(0.2, 1.0))

    def _finish_screen(self, p, cur_task, t, cal):
        q = self.sis["quadro"]
        for c in q.candidates(cur_task["vaga"], "triagem"):
            q.move_candidate(t, c[0], "entrevista" if c[4] > 0.55 else "reprovado")

    def _finish_schedule_interview(self, p, cur_task, t, cal):
        q = self.sis["quadro"]
        v = q.db.execute("SELECT * FROM vagas WHERE id=?", (cur_task["vaga"],)).fetchone()
        cands = q.candidates(cur_task["vaga"], "entrevista")
        if v is None or not cands:
            return
        leader = None
        for x in self.active_people():
            if x.team == v[1] and x.role in ("líder técnico", "coordenador de atendimento", "gerente de vendas", "líder de produto"):
                leader = x
                break
        people = [p.id] + ([leader.id] if leader else [])
        begin = self.sis["agenda"].first_free_slot(people, cal.absolute + MINUTES_PER_DAY, 60)
        if begin is None:
            return
        rid = self.sis["agenda"].schedule(t, "entrevista", "gestão", begin, 60, people, "entrevista com candidato")
        self.on_end[rid] = ("entrevista", cur_task["vaga"], cands[0][0])

    def _finish_close_opening(self, p, cur_task, t, cal):
        q = self.sis["quadro"]
        v = q.db.execute("SELECT * FROM vagas WHERE id=?", (cur_task["vaga"],)).fetchone()
        cands = q.candidates(cur_task["vaga"], "proposta")
        if v is None or not cands:
            return
        if v[6] != "aberta":
            return
        if p.s.random() < 0.75:
            q.move_candidate(t, cands[0][0], "contratado")
            for other in cands[1:] + q.candidates(v[0], "entrevista") + q.candidates(v[0], "triagem"):
                q.move_candidate(t, other[0], "dispensado")
            q.update_opening(t, v[0], "em contratação")
            start = t + p.s.randint(10, 18) * MINUTES_PER_DAY - cal.minute
            self.hires = getattr(self, "hires", [])
            self.hires.append((start, v[0], v[1], v[2], v[3]))
        else:
            q.move_candidate(t, cands[0][0], "desistiu")

    def _choose_owner(self, p, t, cal):
        return {"tipo": "interno", "resta": p.s.randint(30, 90)}

    # ---------- meetings that end in a decision ----------
    def _on_interview_end(self, t, action):
        _, opening, cand = action
        q = self.sis["quadro"]
        c = q.db.execute("SELECT * FROM candidatos WHERE id=?", (cand,)).fetchone()
        if c is not None and c[2] == "entrevista":
            q.move_candidate(t, cand, "proposta" if c[4] > 0.7 else "reprovado")

    def _departures_and_notices(self, t, cal):
        q = self.sis["quadro"]
        for p in self.people:
            if not p.active:
                continue
            if p.quits_at is not None and t >= p.quits_at - 18 * 60:
                p.active = False
                p.present = False
                q.dismiss(t, p.id)
                q.month["saídas"] += 1
                self.sis["agenda"].unschedule_person(p.id, cal.absolute)
                workflow = self.sis["fluxo"]
                for r in workflow.items(states=("em desenvolvimento", "em andamento"), assignee=p.id):
                    if r["tipo"] in ("história", "tarefa", "bug"):
                        workflow.transition(t, r["id"], "pronto para desenvolver", "desenvolvimento")
                    self.remaining.pop(r["id"], None)
                workflow.db.execute("UPDATE itens SET responsavel=NULL WHERE responsavel=? AND estado NOT IN ('liberado', 'concluído', 'fechado')", (p.id,))
                opening = q.open_position(t, p.team, p.role, p.project, "reposição")
                self.sis["eventos"].append((t, f"saída de uma pessoa da equipe de {p.team}"))
                self.sis["verdade"].staff_event(t, "saída", p.team)
                continue
            if p.quits_at is None and p.role not in ("dono",):
                extra = sum(m for d, m in p.recent_overtime if d > cal.date - 14)
                chance = 0.001 * (1.0 + (2.0 if extra > 600 else 0.0))
                if p.s.random() < chance:
                    p.quits_at = t + p.s.randint(15, 30) * MINUTES_PER_DAY
                    self.sis["eventos"].append((t, f"uma pessoa da equipe de {p.team} pediu demissão"))

    def _hiring(self, t, cal):
        q = self.sis["quadro"]
        for pending_hire in list(getattr(self, "hires", [])):
            start, opening, team, role, project = pending_hire
            if t >= start:
                self.hires.remove(pending_hire)
                hire = self._new_person(t, team, role, project)
                hire.speed *= 0.7
                hire.date = cal.date
                base = cal.date * MINUTES_PER_DAY
                hire.arrives_at = base + hire.start
                hire.leaves_at = hire.arrives_at + 540
                hire.lunch_start = base + hire.lunch
                hire.lunch_end = hire.lunch_start + 60
                q.update_opening(t, opening, "preenchida")
                q.month["entradas"] += 1
                self.sis["eventos"].append((t, f"contratação na equipe de {team}"))
                self.sis["verdade"].staff_event(t, "contratação", team)
        # support asks for more people when the queue stays high for several days in a row
        queue = self.sis["fluxo"].count("SUP", "chamado", ("aberto", "em atendimento"))
        n_support = len(self.team_members("atendimento"))
        self.high_queue_days = self.high_queue_days + 1 if queue > 4 * n_support else 0
        if self.high_queue_days >= 5 and t - self.growth_opening_at > 30 * MINUTES_PER_DAY:
            self.growth_opening_at = t
            q.open_position(t, "atendimento", "analista de atendimento", "SUP", "crescimento")

    def _daily_management(self, t, cal):
        """The owner reads the previous day's report: if escalations spiked, calls the leads to an alignment meeting."""
        owner = self.owner()
        if owner is None:
            return
        if getattr(self, "escalations_yesterday", 0) >= 12 and self.alignment_day != cal.date:
            self.alignment_day = cal.date
            leaders = [p.id for p in self.active_people() if p.role in ("dono", "líder técnico", "coordenador de atendimento", "líder de produto")]
            begin = self.sis["agenda"].first_free_slot(leaders, cal.absolute + 8 * 60, 45)
            if begin is not None:
                self.sis["agenda"].schedule(t, "alinhamento", "gestão", begin, 45, leaders, "alinhamento sobre os chamados de ontem")
        self.escalations_yesterday = self.escalations_today

    # ======================================================================================================== operations
    def _development_urgencies(self, t, cal):
        """A critical bug with nobody on it: the squad's on-call developer (or whoever is free) drops what they are doing and takes it."""
        workflow = self.sis["fluxo"]
        busy = self.sis["agenda"].busy
        for project in ("PROD", "PLAT"):
            r = workflow.items(project=project, kind="bug", states=("aberto", "triagem", "pronto para desenvolver"), assignee=None,
                            extra=" AND prioridade='crítica'", order_by="id", limit=1)
            if not r:
                continue
            devs = [p for p in self.active_people() if p.group == "dev" and p.project == project and p.present and p.id not in busy
                    and not (p.task is not None and (p.task.get("urgente") or p.task["tipo"] == "investigar"))]
            if not devs:
                continue
            week = cal.date // 7
            n = len(devs)
            devs.sort(key=lambda p: (0 if p.id % n == week % n else 1, p.id))
            p = devs[0]
            if p.task is not None:
                p.suspended = p.task
            p.task = self._take(p, t, r[0], "investigar", p.s.randint(30, 120) / p.speed)
            p.task["urgente"] = True

    def _on_call(self, cal):
        ops = self.team_members("operação")
        if not ops:
            return None
        return ops[(cal.date // 7) % len(ops)]

    def _operations(self, t, cal):
        """What operations sees every minute: the probe, the alerts, the release windows, the requests for hotfixes."""
        product = self.sis["produto"]
        a = cal.absolute
        # ---- the probe: the product stopped responding ----
        if product.probe_fail_streak >= 3 and self.incident is None:
            working_hours = cal.workday and 8 * 60 <= cal.minute < 19 * 60
            wait = (self.s.lognormvariate(math.log(5), 0.5) if working_hours else self.s.lognormvariate(math.log(18), 0.45))
            self.incident = {"inicio": t, "aviso": t + int(wait), "item": None, "quem": None, "resolvido": False}
            self.sis["eventos"].append((t, "o produto parou de responder"))
        inc = self.incident
        if inc is not None and inc["quem"] is None and t >= inc["aviso"]:
            who = None
            for p in self.team_members("operação"):
                if p.present and p.id not in self.sis["agenda"].busy and not (p.task and p.task.get("urgente")):
                    who = p
                    break
            if who is None:
                who = self._on_call(cal)
            if who is not None:
                inc["quem"] = who.id
                workflow = self.sis["fluxo"]
                inc["item"] = workflow.create(t, "INFRA", "bug", "produto fora do ar", priority="crítica", component="infra",
                                          team="operação", actor="operação", origin="monitoramento")
                workflow.transition(t, inc["item"], "em desenvolvimento", "operação")
                dur = who.s.randint(8, 20) if self.runbook else who.s.randint(22, 50)
                if who.task is not None and not who.task.get("urgente"):
                    who.suspended = who.task
                who.task = {"tipo": "incidente", "resta": dur, "urgente": True}
                who.idle_until = 0
        if inc is not None and inc["resolvido"] and product.probe_fail_streak == 0:
            self.incident = None
        # ---- error, slowness, memory and queue alerts (seen by whoever is in operations) ----
        if cal.minute % 5 == 0:
            self._evaluate_alerts(t, cal)
        if self.alerts:
            for p in self.team_members("operação"):
                if p.present and p.task is None or (p.present and p.task is not None and p.task["tipo"] in ("interno", "tarefa_infra")):
                    if p.id in self.sis["agenda"].busy:
                        continue
                    key = sorted(self.alerts)[0]
                    if p.s.random() < 0.07:
                        alert = self.alerts.pop(key)
                        self.silenced[key] = t + 6 * 60
                        if p.task is not None:
                            p.suspended = p.task
                        p.task = {"tipo": "alerta", "resta": p.s.randint(12, 35), "chave": key, "alerta": alert}
                        break
        # ---- releases: Tuesday and Thursday afternoons; end of sprint on Friday morning; hotfix when there is one ----
        if cal.workday:
            regular = cal.weekday in (1, 3) and 15 * 60 <= cal.minute < 16 * 60
            sprint_end = cal.sprint_day == 11 and 11 * 60 <= cal.minute < 12 * 60
            if (regular or sprint_end) and t - self.last_release > 12 * 60 and self.incident is None:
                freeze = self.sis["fluxo"].db.execute(
                    "SELECT COUNT(*) FROM itens WHERE tipo='bug' AND origem='monitoramento' AND prioridade='crítica' AND estado IN "
                    "('aberto', 'triagem', 'pronto para desenvolver', 'em desenvolvimento', 'em qualidade') AND criado_em > ?",
                    (t - 3 * MINUTES_PER_DAY,)).fetchone()[0]
                if self.sis["repo"].pending_deploy[1] > 0 and not freeze:
                    who = self._free_ops()
                    if who is not None:
                        self.last_release = t
                        who.suspended = who.task if who.task and not who.task.get("urgente") else who.suspended
                        who.task = {"tipo": "liberar", "resta": who.s.randint(15, 35), "origem": "regular"}
        if self.hotfix:
            working_hours = cal.workday and 8 * 60 <= cal.minute < 19 * 60
            critical = any(self.sis["fluxo"].item(b)["prioridade"] == "crítica" for b in self.hotfix)
            if working_hours or critical:
                who = self._free_ops() if working_hours else self._on_call(cal)
                if who is not None and not (who.task and who.task["tipo"] in ("liberar", "corrigir_no_ar", "incidente")):
                    bugs, self.hotfix = self.hotfix, []
                    if who.task and not who.task.get("urgente"):
                        who.suspended = who.task
                    who.task = {"tipo": "corrigir_no_ar", "resta": who.s.randint(10, 25), "bugs": bugs, "urgente": not working_hours}

    def _free_ops(self):
        for p in self.team_members("operação"):
            if p.present and p.id not in self.sis["agenda"].busy and not (p.task and p.task.get("urgente")) \
                    and not (p.task and p.task["tipo"] in ("liberar", "corrigir_no_ar", "alerta")):
                return p
        return None

    def _evaluate_alerts(self, t, cal):
        product = self.sis["produto"]
        for route in product.latency_history:
            key = ("erros", route)
            if self.silenced.get(key, 0) > t or key in self.alerts:
                continue
            req, err = product.errors_in_window(route, 10)
            if err >= 20 and err >= 0.10 * max(1, req):
                self.alerts[key] = {"t": t, "rota": route, "tipo": "erros"}
        for route in product.latency_history:
            key = ("lentidão", route)
            if self.silenced.get(key, 0) > t or key in self.alerts:
                continue
            usual = product.usual_latency(route)
            now = product.latency_in_window(route, 15)
            if usual is not None and now > 2.5 * usual and now > 400:
                self.alerts[key] = {"t": t, "rota": route, "tipo": "lentidão"}
        key = ("fila", "fila")
        pend = product.queue_pending
        if pend > 150 and self.silenced.get(key, 0) <= t and key not in self.alerts:
            self.alerts[key] = {"t": t, "rota": "fila", "tipo": "fila"}
        key = ("memória", "processo")
        crashes = sum(1 for x in product.errors if x[1] == "processo" and x[0] > t - MINUTES_PER_DAY)
        if crashes >= 2 and self.silenced.get(key, 0) <= t and key not in self.alerts:
            self.alerts[key] = {"t": t, "rota": "processo", "tipo": "memória"}

    def _choose_ops(self, p, t, cal):
        workflow = self.sis["fluxo"]
        s = p.s
        sp = workflow.current_sprint("INFRA")
        r = workflow.items(project="INFRA", kind="tarefa", states=("pronto para desenvolver", "backlog"), assignee=None,
                        order_by=PRIO_ORDER_SQL + ", id", limit=1, extra=" AND COALESCE(origem, '') <> 'porta'")
        if r and (sp is not None or r[0]["prioridade"] in ("alta", "crítica")):
            workflow.transition(t, r[0]["id"], "em andamento", "operação")
            workflow.assign_to(r[0]["id"], p.id)
            return {"tipo": "tarefa_infra", "resta": (r[0]["pontos"] or 1) * s.randint(100, 220), "item": r[0]["id"]}
        return {"tipo": "interno", "resta": s.randint(20, 50)}

    def _finish_infra_task(self, p, cur_task, t, cal):
        workflow = self.sis["fluxo"]
        r = workflow.item(cur_task["item"])
        if r is not None and r["estado"] == "em andamento":
            workflow.transition(t, r["id"], "concluído", "operação")
            if "procedimento" in r["titulo"]:
                self.runbook = True

    def _finish_incident(self, p, cur_task, t, cal):
        """The diagnosis is over: the database volume is full. Purge old audit rows and grow the volume, with weeks of headroom."""
        product = self.sis["produto"]
        workflow = self.sis["fluxo"]
        inc = self.incident
        s = p.s
        full = product.volume_pages - product.pages_in_use() < 200
        if full:
            days = s.randint(2, 6)
            deleted = product.purge_old_audit(t, days)
            hist = list(product.daily_pages)
            if len(hist) >= 2:
                growth = max(50.0, (hist[-1][1] - hist[0][1]) / max(1.0, (hist[-1][0] - hist[0][0]) / MINUTES_PER_DAY))
            else:
                growth = 600.0
            headroom = s.randint(21, 35)
            product.grow_volume(product.pages_in_use() + int(growth * headroom))
            text = f"volume do banco cheio; apagamos {deleted} registros de auditoria e aumentamos o volume para cerca de {headroom} dias de folga"
            self.sis["verdade"].incident_resolved(t, "volume do banco cheio", headroom, deleted)
        else:
            product.restarting_until = 0
            text = "processo reiniciado"
            self.sis["verdade"].incident_resolved(t, "processo parado", 0, 0)
        if inc is not None:
            inc["resolvido"] = True
            if inc["item"] is not None:
                workflow.comment(t, inc["item"], "operação", text)
                workflow.transition(t, inc["item"], "liberado", "operação")
        self.sis["eventos"].append((t, "o produto voltou a responder"))
        # the post-incident review on the next workday
        involved = [x.id for x in self.team_members("operação")] + [x.id for x in self.active_people() if x.role in ("dono", "líder técnico", "coordenador de atendimento")]
        begin = self.sis["agenda"].first_free_slot(involved, cal.absolute + 12 * 60, 60)
        if begin is not None:
            rid = self.sis["agenda"].schedule(t, "alinhamento", "operação", begin, 60, involved, "pós-incidente")
            self.on_end[rid] = ("pós-incidente", None)

    def _finish_alert(self, p, cur_task, t, cal):
        """Investigate an alert: read the error log (the traceback names the function), see whether it started after the last release."""
        product = self.sis["produto"]
        repo = self.sis["repo"]
        workflow = self.sis["fluxo"]
        alert = cur_task["alerta"]
        route = alert["rota"]
        if alert["tipo"] == "erros":
            recent = [e for e in product.errors if e[1] == route and e[0] > t - 60]
        elif alert["tipo"] == "fila":
            recent = [e for e in product.errors if e[1] == "fila" and e[0] > t - 120]
        elif alert["tipo"] == "memória":
            recent = [e for e in product.errors if e[1] == "processo" and e[0] > t - MINUTES_PER_DAY]
        else:
            recent = [e for e in product.slow_requests if e[1] == route and e[0] > t - 60]
        functions = sorted({e[2] for e in recent if e[2] is not None})
        if not recent:
            return
        last_deploy = repo.db.execute("SELECT t, versao, tipo FROM implantacoes ORDER BY id DESC LIMIT 1").fetchone()
        comp = codebase.FUNCTION_COMPONENT[functions[0]] if functions else ROUTE_COMPONENT.get(route, "infra")
        project = COMPONENT_PROJECT.get(comp, "PLAT")
        if project == "INFRA":
            project = "PLAT"
        if alert["tipo"] == "erros" and last_deploy is not None and t - last_deploy[0] < 36 * 60 and last_deploy[2] != "reversão":
            before = [e for e in product.errors if e[1] == route and last_deploy[0] - 600 < e[0] < last_deploy[0] and e[2] in functions]
            req30, err30 = product.errors_in_window(route, 30)
            if functions and not before and repo.previous != repo.live and err30 >= 0.25 * max(1, req30) and last_deploy[2] == "regular":
                self.rollback_to = repo.previous
                p.suspended = None
                p.task = {"tipo": "reverter", "resta": p.s.randint(8, 18), "urgente": True}
        title = {"erros": f"erros em {route} no ar", "lentidão": f"{route} lento no ar", "fila": "fila de trabalhos crescendo",
                  "memória": "processo caindo por falta de memória"}[alert["tipo"]]
        opened = workflow.db.execute("SELECT id FROM itens WHERE tipo='bug' AND componente=? AND estado NOT IN ('liberado', 'não reproduzido') "
                                  "AND origem='monitoramento' ORDER BY id DESC LIMIT 1", (comp,)).fetchone()
        if opened is None:
            bug = workflow.create(t, project, "bug", title, priority="crítica" if alert["tipo"] in ("erros", "memória") else "alta",
                              component=comp, team="desenvolvimento", actor="operação", origin="monitoramento")
            workflow.comment(t, bug, "operação", "rastro aponta " + (", ".join(functions) if functions else "nada no código"))

    def _finish_rollback(self, p, cur_task, t, cal):
        repo = self.sis["repo"]
        version = self.rollback_to
        self.rollback_to = None
        if version is None:
            return
        self.sis["produto"].deploy(t, repo.versions[version], version)
        before = repo.versions[repo.live]
        repo.record_deployment(t, version, "reversão", "operação")
        self.sis["verdade"].deployment(t, version, "reversão", before, repo.versions[version], [], self.sis["produto"])
        self.sis["eventos"].append((t, f"versão anterior {version} restaurada"))

    def _finish_release(self, p, cur_task, t, cal):
        repo = self.sis["repo"]
        workflow = self.sis["fluxo"]
        if repo.pending_deploy[1] == 0:
            return
        before = repo.versions[repo.live]
        version = repo.build_version(t, repo.main_branch, "regular")
        self.sis["produto"].deploy(t, repo.main_branch, version)
        repo.record_deployment(t, version, "regular", "operação")
        items = workflow.items(states=("pronto para liberar",), kind=("história", "tarefa", "bug"))
        funcs = []
        for r in items:
            workflow.transition(t, r["id"], "liberado", "operação")
            workflow.link_version(t, r["id"], version)
            if r["id"] in self.feature_story:
                funcs.append(self.feature_story[r["id"]])
            if r["epico"] is not None:
                remaining_n = workflow.db.execute("SELECT COUNT(*) FROM itens WHERE epico=? AND estado NOT IN ('liberado')", (r["epico"],)).fetchone()[0]
                if remaining_n == 0:
                    workflow.transition(t, r["epico"], "concluído", "operação")
                    for c in self.commitments:
                        if c["epico"] == r["epico"]:
                            c["entregue"] = t
            for o in workflow.links_from(r["id"], "causado por"):
                linked = workflow.item(o)
                if linked is not None and linked["estado"] in ("em desenvolvimento", "em andamento"):
                    workflow.transition(t, o, "liberado", "operação")
        self.commitments = [c for c in self.commitments if "entregue" not in c]
        self.sis["verdade"].deployment(t, version, "regular", before, repo.main_branch, funcs, self.sis["produto"])
        self.sis["eventos"].append((t, f"liberação da versão {version} com {len(items)} itens"))

    def _finish_hotfix(self, p, cur_task, t, cal):
        repo = self.sis["repo"]
        workflow = self.sis["fluxo"]
        before = repo.versions[repo.live]
        cod = dict(before)
        hf = getattr(self, "hotfix_functions", {})
        for b in cur_task["bugs"]:
            cod.update(hf.pop(b, {}))
        if cod == before:
            return
        version = repo.build_version(t, cod, "correção")
        self.sis["produto"].deploy(t, cod, version)
        repo.record_deployment(t, version, "correção", "operação")
        for b in cur_task["bugs"]:
            r = workflow.item(b)
            if r is not None and r["estado"] == "pronto para liberar":
                workflow.transition(t, b, "liberado", "operação")
                workflow.link_version(t, b, version)
                for o in workflow.links_from(b, "causado por"):
                    linked = workflow.item(o)
                    if linked is not None and linked["estado"] in ("em desenvolvimento", "em andamento"):
                        workflow.transition(t, o, "liberado", "operação")
        self.sis["verdade"].deployment(t, version, "correção", before, cod, [], self.sis["produto"])
        self.sis["eventos"].append((t, f"correção no ar: versão {version}"))


PLAN_VALUE = {"básico": 290.0 * 12, "pro": 790.0 * 12, "empresarial": 2490.0 * 12}
