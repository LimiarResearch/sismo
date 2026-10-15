"""The acts interface: an optional scenario-injection interface through which questions, requests and meeting calls are sent to
the company's teams. An act is a "pergunta" (question), a "pedido" (request) or a "convocacao" (meeting call) addressed to a team.
On the next step it becomes something inside the company: an item in the workflow tracker (product, development, quality,
operations), a support ticket, a task in the sales CRM, or a request to management. Inside the world the origin of these items is
called "porta"; otherwise they are ordinary items and enter the same queues and counts.

Someone in the team picks the item up in queue order, between tasks, during working hours and outside meetings, and spends time on
it. The response is a short text built from what the team's systems show at that moment. A request makes the team act: operations
runs the route's tests against the live version and, if something fails, rolls back or opens a fix; quality reruns the tests;
support moves the component's tickets to the front of the queue; and so on. A meeting call becomes a meeting in the team's first
free slot. Anything not handled by the end of the next workday goes unanswered."""
import unicodedata

from .catalog import TEAMS, ROUTES, ROUTE_NAME, ROUTE_COMPONENT, COMPONENT_NAME, COMPONENT_PROJECT, MINUTES_PER_DAY
from .product import run_tests

TYPES = ("pergunta", "pedido", "convocacao")
ROUTE_KEYWORDS = {"login": ("login", "entrar", "acesso", "senha"), "catalogo": ("catalogo",), "busca": ("busca", "pesquisa"),
                 "produto": ("produto",), "carrinho": ("carrinho",), "frete": ("frete", "cep", "entrega", "transportadora"),
                 "pedido": ("pedido", "compra", "quantidade"), "pagamento": ("pagamento", "cartao", "cobranca"),
                 "relatorio": ("relatorio",), "exportacao": ("exporta",), "notas": ("nota", "fiscal"), "conta": ("conta", "cadastro", "telefone")}


def _plain(text):
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def route_from_text(text):
    t = _plain(text)
    for route in ROUTES:
        for word in ROUTE_KEYWORDS[route]:
            if word in t:
                return route
    return None


def _fmt_time(abs_min):
    d, m = divmod(abs_min, MINUTES_PER_DAY)
    return f"dia {d}, {m // 60:02d}h{m % 60:02d}"


class ActsInbox:
    def __init__(self, deaf=False):
        self.deaf = deaf
        self.number = 0
        self.incoming = []
        self.acts = {}
        self.queue = {e: [] for e in TEAMS}
        self.output = []

    # ---------- outside side ----------
    def receive(self, team, kind, text):
        if team not in TEAMS:
            raise ValueError(f"unknown team: {team}; the teams are {', '.join(TEAMS)}")
        if kind not in TYPES:
            raise ValueError(f"unknown act kind: {kind}; the kinds are {', '.join(TYPES)}")
        self.number += 1
        if not self.deaf:
            self.incoming.append((self.number, team, kind, str(text)))
        return self.number

    def responses(self):
        output, self.output = self.output, []
        return output

    # ---------- the act becomes something inside the world ----------
    def materialize(self, t, cal, sis):
        if not self.incoming:
            return
        incoming, self.incoming = self.incoming, []
        workflow = sis["fluxo"]
        for number, team, kind, text in incoming:
            route = route_from_text(text)
            comp = ROUTE_COMPONENT[route] if route else None
            title = text[:120]
            if team == "atendimento":
                item = workflow.create(t, "SUP", "chamado", title, priority="média", component=comp, team=team, actor="porta",
                                   channel="interno", origin="porta", protocol_no=number)
                system = "fluxo"
            elif team == "vendas":
                item = sis["crm"].new_task(t, title, number)
                system = "crm"
            elif team == "gestão":
                item = sis["quadro"].request(t, "pedido interno", title, protocol_no=number)
                system = "quadro"
            else:
                project = "INFRA" if team == "operação" else ("PLAT" if comp and COMPONENT_PROJECT.get(comp) == "PLAT" else "PROD")
                item = workflow.create(t, project, "tarefa", title, priority="média", component=comp or ("infra" if project == "INFRA" else None),
                                   team=team, actor="porta", origin="porta", protocol_no=number)
                system = "fluxo"
            # the deadline: end of working hours on the next workday
            d = cal.date + 1
            while d % 7 >= 5:
                d += 1
            deadline = t + (d * MINUTES_PER_DAY + 18 * 60 - cal.absolute)
            self.acts[number] = {"numero": number, "equipe": team, "tipo": kind, "texto": text, "rota": route, "componente": comp,
                                 "sistema": system, "item": item, "criado": t, "prazo": deadline, "estado": "aberto"}
            self.queue[team].append(number)
            sis["verdade"].act(t, number, team, kind)

    def next_due(self, team, t):
        queue = self.queue[team]
        while queue:
            number = queue.pop(0)
            act = self.acts[number]
            if act["estado"] == "aberto":
                act["estado"] = "em tratamento"
                return act
        return None

    def expire(self, t, sis):
        for number, act in self.acts.items():
            if act["estado"] in ("aberto", "em tratamento") and t >= act["prazo"]:
                act["estado"] = "sem resposta"
                self._close(t, act, sis, "descartado")
                if number in self.queue[act["equipe"]]:
                    self.queue[act["equipe"]].remove(number)

    def _close(self, t, act, sis, how):
        if act["sistema"] == "fluxo":
            r = sis["fluxo"].item(act["item"])
            if r is None:
                return
            if r["tipo"] == "chamado":
                if how == "descartado":
                    sis["fluxo"].transition(t, act["item"], "descartado", "atendimento")
                else:
                    sis["fluxo"].transition(t, act["item"], "resolvido", "atendimento")
                    sis["fluxo"].transition(t, act["item"], "fechado", "atendimento")
            else:
                sis["fluxo"].transition(t, act["item"], "descartado" if how == "descartado" else "concluído", act["equipe"])
        elif act["sistema"] == "crm":
            sis["crm"].close_task(t, act["item"], "descartada" if how == "descartado" else "concluída")
        else:
            sis["quadro"].complete_request(t, act["item"], "descartada" if how == "descartado" else "concluída")

    # ---------- someone in the team handles the act ----------
    def handle(self, number, person, t, cal, company):
        act = self.acts.get(number)
        if act is None or act["estado"] != "em tratamento":
            return
        sis = company.sis
        if act["sistema"] == "fluxo":
            r = sis["fluxo"].item(act["item"])
            if r is not None and r["tipo"] == "chamado":
                sis["fluxo"].transition(t, act["item"], "em atendimento", "atendimento")
            elif r is not None:
                sis["fluxo"].transition(t, act["item"], "em andamento", act["equipe"])
            sis["fluxo"].comment(t, act["item"], act["equipe"], "tratado")
        if act["tipo"] == "convocacao":
            text = self._convene(act, person, t, cal, company)
        else:
            text = getattr(self, "_" + {"produto": "product", "desenvolvimento": "development", "qualidade": "quality",
                                         "atendimento": "support", "vendas": "sales", "operação": "operations",
                                         "gestão": "management"}[act["equipe"]])(act, person, t, cal, company)
        act["estado"] = "respondido"
        self._close(t, act, sis, "concluído")
        self.output.append((t, number, act["equipe"], text))
        sis["verdade"].act_answered(t, number)

    # ---------- what each team looks at ----------
    def _route_now(self, sis, route, minutes=30):
        prod = sis["produto"]
        req, err = prod.errors_in_window(route, minutes)
        lat = prod.latency_in_window(route, minutes)
        return req, err, lat

    def _version_text(self, sis):
        repo = sis["repo"]
        r = repo.db.execute("SELECT t FROM implantacoes ORDER BY id DESC LIMIT 1").fetchone()
        when = f", no ar há {(sis['relogio'].t - r[0]) // 60} h" if r else ""
        return f"versão {repo.live}{when}"

    def _operations(self, act, person, t, cal, company):
        sis = company.sis
        prod = sis["produto"]
        free = 100.0 * max(0, prod.volume_pages - prod.pages_in_use()) / max(1, prod.volume_pages)
        base = f"{self._version_text(sis)}; volume do banco com {free:.0f}% livre; fila de trabalhos com {prod.queue_pending}."
        route = act["rota"]
        if route is None:
            errors = sum(prod.errors_in_window(r, 30)[1] for r in ROUTES)
            text = f"Visão geral: {base} {errors} respostas com erro em todas as rotas na última meia hora."
            if act["tipo"] == "pedido":
                text += " Sem rota indicada, não rodamos verificação."
            return text
        req, err, lat = self._route_now(sis, route)
        text = f"Rota {ROUTE_NAME[route]}: {req} requisições, {err} com erro e latência média de {lat:.0f} ms na última meia hora; {base}"
        if act["tipo"] != "pedido":
            return text
        repo = sis["repo"]
        comp = ROUTE_COMPONENT[route]
        n, failures = run_tests(repo.versions[repo.live], comp, person.s, 1.0, run_all=True)
        repo.record_tests(t, comp, "no ar", n, len(failures), "operação")
        if not failures:
            return text + f" Rodamos {n} testes de {COMPONENT_NAME[comp]} contra a versão no ar: todos passam."
        names = "; ".join(sorted({name for _, name, _ in failures}))
        functions = sorted({f for f, _, _ in failures})
        last_deploy = repo.db.execute("SELECT t, tipo FROM implantacoes ORDER BY id DESC LIMIT 1").fetchone()
        previous = repo.versions.get(repo.previous, {})
        came_with_last = last_deploy is not None and t - last_deploy[0] < 2 * MINUTES_PER_DAY and last_deploy[1] != "reversão" and \
            any(previous.get(f) != repo.versions[repo.live].get(f) for f in functions)
        workflow = sis["fluxo"]
        project = COMPONENT_PROJECT.get(comp, "PROD")
        bug = workflow.create(t, "PLAT" if project == "INFRA" else project, "bug", f"falha verificada em {ROUTE_NAME[route]}",
                          priority="crítica", component=comp, team="desenvolvimento", actor="operação", origin="monitoramento")
        workflow.comment(t, bug, "operação", "testes que falham: " + names)
        if came_with_last and company.rollback_to is None:
            company.rollback_to = repo.previous
            person.task = {"tipo": "reverter", "resta": person.s.randint(8, 15), "urgente": True}
            return text + f" Na versão no ar falha: {names}. A falha veio com a última liberação; vamos voltar para a versão {repo.previous} e abrimos a correção."
        return text + f" Na versão no ar falha: {names}. Abrimos a correção com prioridade crítica."

    def _quality(self, act, person, t, cal, company):
        sis = company.sis
        workflow = sis["fluxo"]
        repo = sis["repo"]
        wait = workflow.count(kind=None, states=("em qualidade",))
        exec24 = repo.db.execute("SELECT COUNT(*), COALESCE(SUM(testes), 0), COALESCE(SUM(falhas), 0) FROM execucoes_teste WHERE t > ?",
                                 (t - MINUTES_PER_DAY,)).fetchone()
        text = f"Na qualidade há {wait} itens esperando teste; nas últimas 24 h foram {exec24[0]} execuções, {exec24[1]} testes e {exec24[2]} falhas."
        comp = act["componente"]
        if act["tipo"] != "pedido" or comp is None:
            return text
        n, failures = run_tests(repo.versions[repo.live], comp, person.s, 1.0, run_all=True)
        repo.record_tests(t, comp, "no ar", n, len(failures), "qualidade")
        if not failures:
            return text + f" Refizemos os {n} testes de {COMPONENT_NAME[comp]} na versão no ar: passam."
        reopened = []
        for func_name in sorted({f for f, _, _ in failures}):
            origin = repo.authorship.get(func_name)
            bug = workflow.create(t, COMPONENT_PROJECT.get(comp, "PROD"), "bug", f"teste refeito falha em {COMPONENT_NAME[comp]}",
                              priority="alta", component=comp, team="desenvolvimento", actor="qualidade", origin="qualidade")
            if origin is not None:
                o = workflow.item(origin)
                workflow.connect(t, bug, origin, "causado por")
                if o is not None and o["estado"] == "liberado" and o["tipo"] in ("história", "tarefa") and \
                        repo.main_branch.get(func_name) == repo.versions[repo.live].get(func_name):
                    workflow.transition(t, origin, "em desenvolvimento" if o["tipo"] != "tarefa" else "em andamento", "qualidade")
                    reopened.append(o["chave"])
        names = "; ".join(sorted({name for _, name, _ in failures}))
        return text + f" Refizemos os testes de {COMPONENT_NAME[comp]} na versão no ar e falha: {names}." + \
            (f" Reabrimos {', '.join(reopened)}." if reopened else " Abrimos um bug.")

    def _development(self, act, person, t, cal, company):
        sis = company.sis
        workflow = sis["fluxo"]
        comp = act["componente"]
        in_dev = workflow.count(states=("em desenvolvimento", "em andamento"))
        in_review = workflow.count(states=("em revisão",))
        text = f"No desenvolvimento há {in_dev} itens em andamento e {in_review} em revisão."
        if comp is None:
            return text
        bugs = workflow.db.execute("SELECT id, chave, prioridade FROM itens WHERE tipo='bug' AND componente=? AND estado NOT IN "
                                "('liberado', 'não reproduzido') ORDER BY id", (comp,)).fetchall()
        text += f" Bugs abertos em {COMPONENT_NAME[comp]}: {len(bugs)}."
        if act["tipo"] != "pedido":
            return text
        if bugs:
            target = bugs[-1]
            if target["prioridade"] != "crítica":
                workflow.set_priority(target["id"], "crítica")
            return text + f" Passamos o {target['chave']} para prioridade crítica; quem estiver livre pega agora."
        repo = sis["repo"]
        n, failures = run_tests(repo.versions[repo.live], comp, person.s, 1.0, run_all=True)
        repo.record_tests(t, comp, "no ar", n, len(failures), "desenvolvimento")
        if not failures:
            return text + f" Rodamos os {n} testes do componente na versão no ar: passam."
        bug = workflow.create(t, COMPONENT_PROJECT.get(comp, "PROD"), "bug", f"falha encontrada em {COMPONENT_NAME[comp]}",
                          priority="crítica", component=comp, team="desenvolvimento", actor="desenvolvimento", origin="monitoramento")
        return text + f" Na versão no ar falha: {'; '.join(sorted({nm for _, nm, _ in failures}))}. Abrimos {workflow.item(bug)['chave']} como crítico."

    def _support(self, act, person, t, cal, company):
        workflow = company.sis["fluxo"]
        open_count = workflow.count("SUP", "chamado", ("aberto", "em atendimento", "aguardando cliente", "escalado"))
        unanswered = workflow.count("SUP", "chamado", ("aberto",))
        text = f"No atendimento há {open_count} chamados abertos, {unanswered} ainda sem primeira resposta."
        comp = act["componente"]
        if comp is not None:
            n = workflow.count("SUP", "chamado", ("aberto", "em atendimento", "aguardando cliente", "escalado"), component=comp)
            n_escalated = workflow.count("SUP", "chamado", ("escalado",), component=comp)
            text += f" De {COMPONENT_NAME[comp]}: {n} abertos, {n_escalated} escalados."
            if act["tipo"] == "pedido":
                company.support_focus = (comp, t + 240)
                text += f" Nas próximas quatro horas respondemos primeiro os de {COMPONENT_NAME[comp]}."
        return text

    def _sales(self, act, person, t, cal, company):
        crm = company.sis["crm"]
        n = {e: crm.count_in_stage(e) for e in ("lead", "qualificação", "proposta", "negociação")}
        won_count = crm.db.execute("SELECT COUNT(*) FROM negocios WHERE estagio='ganho' AND fechado_em > ?", (t - 7 * MINUTES_PER_DAY,)).fetchone()[0]
        text = (f"No funil: {n['lead']} leads, {n['qualificação']} em qualificação, {n['proposta']} propostas e {n['negociação']} em "
                 f"negociação; {won_count} negócios ganhos nos últimos sete dias.")
        if act["tipo"] == "pedido":
            company.sales_focus = t + 2 * MINUTES_PER_DAY
            text += " Nos próximos dois dias a equipe retoma primeiro as propostas e negociações paradas."
        return text

    def _product(self, act, person, t, cal, company):
        workflow = company.sis["fluxo"]
        backlog = workflow.count(kind="história", states=("backlog", "refinamento"))
        ready = workflow.count(kind="história", states=("pronto para desenvolver",))
        text = f"No produto há {backlog} histórias no backlog e em refinamento e {ready} prontas para desenvolver."
        if act["tipo"] == "pedido":
            comp = act["componente"]
            project = COMPONENT_PROJECT.get(comp, "PROD") if comp else "PROD"
            project = "PLAT" if project == "INFRA" else project
            h = workflow.create(t, project, "história", act["texto"][:120], priority="alta", component=comp, team="desenvolvimento",
                            actor="produto", points=3)
            text += f" Registramos a história {workflow.item(h)['chave']} com prioridade alta."
        return text

    def _management(self, act, person, t, cal, company):
        sis = company.sis
        actives = [p for p in company.people if p.active]
        present_count = sum(1 for p in actives if p.present)
        vacation = sum(1 for p in actives if p.absent == "férias")
        openings, cand = sis["quadro"].opening_counts()
        text = (f"Somos {len(actives)} pessoas; {present_count} trabalhando agora, {vacation} de férias hoje; {openings} vagas abertas com "
                 f"{cand} candidatos; {sis['clientes'].active_count()} clientes ativos.")
        if act["tipo"] == "pedido":
            leaders = [p.id for p in actives if p.role in ("dono", "líder técnico", "coordenador de atendimento", "líder de produto",
                                                           "gerente de vendas")]
            begin = sis["agenda"].first_free_slot(leaders, cal.absolute, 45)
            if begin is not None:
                sis["agenda"].schedule(t, "alinhamento", "gestão", begin, 45, leaders, act["texto"][:80], origin="porta", protocol_no=act["numero"])
                text += f" A direção marcou um alinhamento com as lideranças para {_fmt_time(begin)}."
        return text

    def _convene(self, act, person, t, cal, company):
        sis = company.sis
        members = [p.id for p in company.people if p.active and p.team == act["equipe"]]
        begin = sis["agenda"].first_free_slot(members, cal.absolute, 30)
        if begin is None:
            members = [p.id for p in company.people if p.active and p.team == act["equipe"] and p.absent is None][:6]
            begin = sis["agenda"].first_free_slot(members, cal.absolute, 30)
        if begin is None:
            return "Não achamos horário livre para todos nos próximos dias; tente de novo."
        sis["agenda"].schedule(t, "alinhamento", act["equipe"], begin, 30, members, act["texto"][:80], origin="porta", protocol_no=act["numero"])
        return f"Reunião marcada para {_fmt_time(begin)}, 30 minutos, com {len(members)} pessoas da equipe de {act['equipe']}."
