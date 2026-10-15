"""The connectors: what goes out through the world interface. Each process is an aggregate read from the company systems (the live
product, the database, the queue, the repository, the workflow tracker, the CRM, the calendar, the staff board, the customer base),
by route, component, project, team, stage, queue, plan, region. No field says what matters, none is a normal/abnormal label, none
comes from a single person: they are measures of what the systems did in that minute or of the state they are in.

The list of processes and fields is fixed and always comes out in the same order."""
from .catalog import (ROUTES, ROUTE_NAME, COMPONENTS, COMPONENT_NAME, TEAMS, PLANS, REGIONS, PROJECTS)
from .agenda import TYPES as MEETING_TYPES
from .crm import SOURCES
from .workflow import FINAL_STATES

OPEN_SUP = ("aberto", "em atendimento", "aguardando cliente", "escalado")
NOT_OPEN = set(FINAL_STATES) | {"resolvido"}


def process_list():
    P = []
    for r in ROUTES:
        P.append((f"rota {ROUTE_NAME[r]}", ["requisições no minuto", "respostas com erro no minuto", "respostas recusadas no minuto",
                                           "latência média em ms", "latência do percentil 95 em ms", "clientes distintos no minuto"]))
    P += [("servidor da aplicação", ["uso de processador em %", "memória em uso em MB", "reinícios do processo no minuto"]),
          ("banco do produto", ["tamanho ocupado em MB", "espaço livre no volume em MB", "consultas no minuto", "escritas no minuto",
                                "instruções executadas em milhares"]),
          ("fila de trabalhos", ["trabalhos pendentes", "trabalhos concluídos no minuto", "falhas de trabalho no minuto",
                                 "idade do trabalho pendente mais antigo em minutos"]),
          ("gateway de pagamento", ["chamadas no minuto", "recusas no minuto"]),
          ("transportadoras", ["cotações de frete no minuto", "cotações com erro no minuto"]),
          ("sonda de disponibilidade", ["verificações no minuto", "verificações com falha no minuto"]),
          ("implantação", ["implantações no minuto", "commits incluídos no minuto", "itens incluídos no minuto"]),
          ("tarefas agendadas do servidor", ["tarefas em execução", "linhas processadas no minuto"]),
          ("e-mails do produto", ["enviados no minuto", "com falha no minuto"]),
          ("pedidos", ["pedidos criados no minuto", "valor dos pedidos no minuto em reais", "itens nos pedidos do minuto"]),
          ("pagamentos", ["pagamentos aprovados no minuto", "pedidos pagos no minuto", "pagamentos recusados no minuto"]),
          ("notas fiscais", ["notas emitidas no minuto", "emissões com falha no minuto"]),
          ("estoque", ["produtos sem estoque", "unidades repostas no minuto"]),
          ("sessões dos clientes", ["sessões iniciadas no minuto", "sessões abandonadas depois de erro no minuto", "sessões ativas",
                                    "usuários conectados"]),
          ("faturamento", ["faturas emitidas no minuto", "faturas pagas no minuto", "faturas em aberto", "estornos feitos no minuto"])]
    for g in REGIONS:
        P.append((f"região {g}", ["clientes ativos", "pedidos no minuto", "cotações de frete no minuto", "cotações com erro no minuto"]))
    P.append(("carteira de clientes", ["clientes ativos", "entradas no minuto", "cancelamentos no minuto", "pedidos de cancelamento abertos"]))
    for pl in PLANS:
        P.append((f"clientes do plano {pl}", ["clientes ativos", "sessões ativas", "pedidos no minuto", "chamados abertos no minuto"]))
    P.append(("pesquisa de satisfação", ["respostas no minuto", "soma das notas no minuto"]))
    for channel in ("chat", "e-mail", "telefone"):
        P.append((f"canal de atendimento {channel}", ["contatos recebidos no minuto"]))
    for proj in ("PROD", "PLAT"):
        name = f"projeto {PROJECTS[proj]}"
        P += [(f"{name}: entrada", ["histórias no backlog", "histórias em refinamento", "bugs abertos ou em triagem", "épicos em andamento",
                                    "tarefas no backlog"]),
              (f"{name}: desenvolvimento", ["prontos para desenvolver", "em desenvolvimento", "em revisão", "em qualidade",
                                            "prontos para liberar"]),
              (f"{name}: movimento", ["itens criados no minuto", "transições no minuto", "itens liberados no minuto",
                                      "reprovações no minuto", "reaberturas no minuto", "comentários no minuto"]),
              (f"{name}: sprint", ["itens no sprint", "pontos planejados", "pontos do sprint", "pontos concluídos", "pontos restantes",
                                   "itens de prioridade alta ou crítica no sprint"]),
              (f"{name}: prioridades", ["itens abertos de prioridade baixa", "itens abertos de prioridade média",
                                        "itens abertos de prioridade alta", "itens abertos de prioridade crítica"]),
              (f"{name}: idade", ["itens abertos", "idade média dos itens abertos em horas"])]
    P += [("projeto Infraestrutura: itens", ["tarefas no backlog", "tarefas prontas", "em andamento", "bugs abertos", "concluídos no minuto"]),
          ("projeto Infraestrutura: movimento", ["itens criados no minuto", "transições no minuto", "comentários no minuto"]),
          ("projeto Infraestrutura: sprint", ["itens no sprint", "pontos planejados", "pontos do sprint", "pontos concluídos", "pontos restantes",
                                              "itens de prioridade alta ou crítica no sprint"]),
          ("projeto Infraestrutura: prioridades", ["itens abertos de prioridade baixa", "itens abertos de prioridade média",
                                                   "itens abertos de prioridade alta", "itens abertos de prioridade crítica"]),
          ("projeto Infraestrutura: idade", ["itens abertos", "idade média dos itens abertos em horas"]),
          ("projeto Suporte: chamados por estado", ["abertos sem primeira resposta", "em atendimento", "aguardando cliente", "escalados",
                                                    "resolvidos aguardando fechamento"]),
          ("projeto Suporte: movimento", ["chamados novos no minuto", "primeiras respostas no minuto", "resolvidos no minuto",
                                          "fechados no minuto", "reabertos no minuto", "comentários no minuto"]),
          ("projeto Suporte: prazos", ["chamados fora do prazo de primeira resposta", "espera do chamado mais antigo sem resposta em minutos"]),
          ("projeto Suporte: prioridades", ["chamados abertos de prioridade baixa", "chamados abertos de prioridade média",
                                            "chamados abertos de prioridade alta", "chamados abertos de prioridade crítica"]),
          ("projeto Suporte: sprint", ["itens no sprint", "pontos planejados", "pontos do sprint", "pontos concluídos", "pontos restantes",
                                       "itens de prioridade alta ou crítica no sprint"]),
          ("projeto Suporte: idade", ["chamados abertos", "idade média dos chamados abertos em horas"])]
    for c in COMPONENTS:
        P.append((f"chamados de {COMPONENT_NAME[c]}", ["abertos", "novos no minuto", "escalados", "resolvidos no minuto"]))
    for c in COMPONENTS:
        P.append((f"bugs de {COMPONENT_NAME[c]}", ["abertos", "criados no minuto", "liberados no minuto"]))
    for e in TEAMS:
        P.append((f"fluxo da equipe de {e}", ["itens abertos sob responsabilidade da equipe", "transições no minuto",
                                              "comentários no minuto", "itens criados no minuto"]))
    P.append(("épicos", ["abertos", "em andamento", "concluídos no minuto"]))
    P.append(("repositório de código", ["commits no minuto", "linhas alteradas no minuto", "revisões aprovadas no minuto",
                                        "revisões que pediram mudança no minuto", "ramos abertos"]))
    for c in COMPONENTS:
        P.append((f"código de {COMPONENT_NAME[c]}", ["commits no minuto", "testes executados no minuto", "testes com falha no minuto"]))
    P.append(("funil de vendas", ["leads", "em qualificação", "propostas", "em negociação", "ganhos no minuto", "perdidos no minuto",
                                  "valor em aberto em milhares de reais"]))
    P.append(("atividades de vendas", ["ligações no minuto", "e-mails no minuto", "propostas enviadas no minuto", "tarefas internas abertas"]))
    for o in SOURCES:
        P.append((f"leads de {o}", ["novos no minuto", "em aberto no funil"]))
    for e in TEAMS:
        P.append((f"agenda da equipe de {e}", ["pessoas em reunião", "reuniões em curso", "minutos de reunião no dia"]))
    for kind in MEETING_TYPES:
        P.append((f"reuniões do tipo {kind}", ["em curso", "pessoas"]))
    for e in TEAMS:
        P.append((f"quadro da equipe de {e}", ["pessoas no quadro", "presentes agora", "em almoço", "ausentes por férias hoje",
                                               "ausentes por falta hoje", "horas extras no dia"]))
    P.append(("quadro geral", ["pessoas no quadro", "entradas no mês", "saídas no mês", "vagas abertas", "candidatos em processo",
                               "solicitações abertas à gestão"]))
    P.append(("ponto", ["entradas registradas no minuto", "saídas registradas no minuto"]))
    return P


class Connectors:
    def __init__(self):
        self.processes = process_list()
        self.meeting_minutes = {e: 0 for e in TEAMS}

    def new_day(self):
        self.meeting_minutes = {e: 0 for e in TEAMS}

    def read(self, t, cal, m, pr):
        """m: the world; pr: the product's tallies for the minute. Returns {process: [values]} in the fixed order."""
        sis = m.sis
        out = {}
        # ---------------------------------------------------------------- product
        routes = pr["rotas"]
        for r in ROUTES:
            n, e, rec, med, p95, cust = routes[r]
            out[f"rota {ROUTE_NAME[r]}"] = [n, e, rec, round(med, 1), round(p95, 1), cust]
        out["servidor da aplicação"] = [round(pr["cpu"], 1), round(pr["memoria"], 1), pr["reinicios"]]
        out["banco do produto"] = [round(pr["paginas"] * 4096 / 1e6, 2), round(pr["livre_paginas"] * 4096 / 1e6, 2), pr["consultas"],
                                   pr["escritas"], round(pr["instrucoes"] / 100.0, 1)]
        out["fila de trabalhos"] = list(pr["fila"])
        out["gateway de pagamento"] = list(pr["gateway"])
        ship_by_region, ship_err_by_region = pr["frete_reg"]
        out["transportadoras"] = [sum(ship_by_region), sum(ship_err_by_region)]
        out["sonda de disponibilidade"] = list(pr["sonda"])
        commits, tests, reviews, impl = sis["repo"].minute(t)
        out["implantação"] = list(impl)
        out["tarefas agendadas do servidor"] = list(pr["cron"])
        out["e-mails do produto"] = list(pr["emails"])
        order_stats = pr["pedidos"]
        out["pedidos"] = [order_stats[0], round(order_stats[1], 2), order_stats[2]]
        out["pagamentos"] = list(pr["pag"])
        out["notas fiscais"] = list(pr["notas"])
        out["estoque"] = [pr["sem_estoque"], pr["repostas"]]
        cust = sis["clientes"]
        cm = cust.min
        by_plan, by_region, sessions_by_plan, users, sessions = cust.counts()
        out["sessões dos clientes"] = [cm["sessoes_iniciadas"], cm["abandonos"], sessions, users]
        try:
            open_invoices = sis["produto"].db.con.execute("SELECT COUNT(*) FROM faturas WHERE estado='aberta'").fetchone()[0]
        except Exception:
            open_invoices = 0
        out["faturamento"] = [pr["faturas_emitidas"], cm["faturas_pagas"], open_invoices, sis["estornos"][0]]
        sis["estornos"][0] = 0
        region_orders = dict(pr["pedidos_reg"])
        for i, g in enumerate(REGIONS):
            out[f"região {g}"] = [by_region[i], region_orders.get(i, 0), ship_by_region[i], ship_err_by_region[i]]
        cancel = sis["quadro"].db.execute("SELECT COUNT(*) FROM solicitacoes WHERE tipo='cancelamento' AND estado IN ('aberta', 'em andamento')").fetchone()[0]
        out["carteira de clientes"] = [sum(by_plan.values()), cm["entradas"], cm["cancelamentos"], cancel]
        plan_orders = dict(pr["pedidos_plano"])
        for pl in PLANS:
            out[f"clientes do plano {pl}"] = [by_plan[pl], sessions_by_plan[pl], plan_orders.get(pl, 0), cm["chamados_plano"][pl]]
        out["pesquisa de satisfação"] = [len(cm["pesquisas"]), sum(cm["pesquisas"])]
        for channel in ("chat", "e-mail", "telefone"):
            out[f"canal de atendimento {channel}"] = [cm["contatos"][channel]]
        # ---------------------------------------------------------------- workflow
        counts, transitions, comments, sprints, awaiting_first = sis["fluxo"].minute(t)
        state_counts = {}
        prio = {p: {"baixa": 0, "média": 0, "alta": 0, "crítica": 0} for p in PROJECTS}
        age = {p: [0, 0] for p in PROJECTS}
        comp_tickets = {c: [0, 0] for c in COMPONENTS}
        comp_bug = {c: 0 for c in COMPONENTS}
        team_open = {e: 0 for e in TEAMS}
        epics = [0, 0]
        for proj, kind, state, priority, comp, team, n, subtotal in counts:
            key = (proj, kind, state)
            state_counts[key] = state_counts.get(key, 0) + n
            opened = state not in NOT_OPEN
            if kind == "épico":
                if state == "aberto":
                    epics[0] += n
                elif state == "em andamento":
                    epics[1] += n
                continue
            if opened:
                prio[proj][priority] += n
                age[proj][0] += n
                age[proj][1] += subtotal
                if team in team_open:
                    team_open[team] += n
            if kind == "chamado" and comp in comp_tickets and state in OPEN_SUP:
                comp_tickets[comp][0] += n
                if state == "escalado":
                    comp_tickets[comp][1] += n
            if kind == "bug" and comp in comp_bug and opened:
                comp_bug[comp] += n
        g = lambda p, tp, e: state_counts.get((p, tp, e), 0)
        moves = {p: {"criados": 0, "trans": 0, "lib": 0, "rep": 0, "reab": 0, "concl": 0} for p in PROJECTS}
        sup = {"novos": 0, "prim": 0, "resolv": 0, "fech": 0, "reab": 0}
        comp_new = {c: [0, 0] for c in COMPONENTS}
        bug_moves = {c: [0, 0] for c in COMPONENTS}
        team_moves = {e: [0, 0] for e in TEAMS}
        epics_done = 0
        for proj, kind, comp, channel, src, dst, actor, reopen in transitions:
            mv = moves[proj]
            mv["trans"] += 1
            if src is None:
                mv["criados"] += 1
            if dst == "liberado":
                mv["lib"] += 1
            if dst in ("liberado", "concluído"):
                mv["concl"] += 1
            if (src == "em qualidade" or src == "em revisão") and dst in ("em desenvolvimento", "em andamento"):
                mv["rep"] += 1
            if reopen:
                mv["reab"] += 1
            if actor in team_moves:
                team_moves[actor][0] += 1
                if src is None:
                    team_moves[actor][1] += 1
            if kind == "épico" and dst == "concluído":
                epics_done += 1
            if kind == "chamado":
                if src is None:
                    sup["novos"] += 1
                    if comp in comp_new:
                        comp_new[comp][0] += 1
                if src == "aberto" and dst not in ("descartado",):
                    sup["prim"] += 1
                if dst == "resolvido":
                    sup["resolv"] += 1
                    if comp in comp_new:
                        comp_new[comp][1] += 1
                if dst == "fechado":
                    sup["fech"] += 1
                if reopen:
                    sup["reab"] += 1
            if kind == "bug" and comp in bug_moves:
                if src is None:
                    bug_moves[comp][0] += 1
                if dst == "liberado":
                    bug_moves[comp][1] += 1
        comments_by_project = {p: 0 for p in PROJECTS}
        comments_by_team = {e: 0 for e in TEAMS}
        for proj, team, n in comments:
            comments_by_project[proj] += n
            if team in comments_by_team:
                comments_by_team[team] += n
        sp = {p: [0, 0, 0, 0, 0, 0] for p in PROJECTS}
        for proj, goal, total, done_points, n, high_prio in sprints:
            sp[proj] = [n, goal or 0, total, done_points, max(0, total - done_points), high_prio]
        age_h = lambda p: (round((t * age[p][0] - age[p][1]) / age[p][0] / 60.0, 1) if age[p][0] else 0.0)
        for proj in ("PROD", "PLAT"):
            name = f"projeto {PROJECTS[proj]}"
            out[f"{name}: entrada"] = [g(proj, "história", "backlog"), g(proj, "história", "refinamento"),
                                       g(proj, "bug", "aberto") + g(proj, "bug", "triagem"), g(proj, "épico", "em andamento"),
                                       g(proj, "tarefa", "backlog")]
            subtotal = lambda e: g(proj, "história", e) + g(proj, "tarefa", e) + g(proj, "bug", e)
            out[f"{name}: desenvolvimento"] = [subtotal("pronto para desenvolver"), subtotal("em desenvolvimento") + g(proj, "tarefa", "em andamento"),
                                               subtotal("em revisão"), subtotal("em qualidade"), subtotal("pronto para liberar")]
            mv = moves[proj]
            out[f"{name}: movimento"] = [mv["criados"], mv["trans"], mv["lib"], mv["rep"], mv["reab"], comments_by_project[proj]]
            out[f"{name}: sprint"] = sp[proj]
            out[f"{name}: prioridades"] = [prio[proj][x] for x in ("baixa", "média", "alta", "crítica")]
            out[f"{name}: idade"] = [age[proj][0], age_h(proj)]
        mv = moves["INFRA"]
        out["projeto Infraestrutura: itens"] = [g("INFRA", "tarefa", "backlog"), g("INFRA", "tarefa", "pronto para desenvolver"),
                                                g("INFRA", "tarefa", "em andamento") + g("INFRA", "bug", "em desenvolvimento"),
                                                sum(state_counts.get(("INFRA", "bug", e), 0) for e in ("aberto", "triagem", "pronto para desenvolver",
                                                                                               "em desenvolvimento", "em qualidade")),
                                                mv["concl"]]
        out["projeto Infraestrutura: movimento"] = [mv["criados"], mv["trans"], comments_by_project["INFRA"]]
        out["projeto Infraestrutura: sprint"] = sp["INFRA"]
        out["projeto Infraestrutura: prioridades"] = [prio["INFRA"][x] for x in ("baixa", "média", "alta", "crítica")]
        out["projeto Infraestrutura: idade"] = [age["INFRA"][0], age_h("INFRA")]
        out["projeto Suporte: chamados por estado"] = [g("SUP", "chamado", e) for e in ("aberto", "em atendimento", "aguardando cliente",
                                                                                         "escalado", "resolvido")]
        out["projeto Suporte: movimento"] = [sup["novos"], sup["prim"], sup["resolv"], sup["fech"], sup["reab"], comments_by_project["SUP"]]
        outside = 0
        oldest = None
        for priority, created in awaiting_first:
            if t - created > {"crítica": 60, "alta": 240, "média": 1440, "baixa": 4320}[priority]:
                outside += 1
            if oldest is None or created < oldest:
                oldest = created
        out["projeto Suporte: prazos"] = [outside, (t - oldest) if oldest is not None else 0]
        out["projeto Suporte: prioridades"] = [prio["SUP"][x] for x in ("baixa", "média", "alta", "crítica")]
        out["projeto Suporte: sprint"] = sp["SUP"]
        out["projeto Suporte: idade"] = [age["SUP"][0], age_h("SUP")]
        for c in COMPONENTS:
            out[f"chamados de {COMPONENT_NAME[c]}"] = [comp_tickets[c][0], comp_new[c][0], comp_tickets[c][1], comp_new[c][1]]
        for c in COMPONENTS:
            out[f"bugs de {COMPONENT_NAME[c]}"] = [comp_bug[c], bug_moves[c][0], bug_moves[c][1]]
        for e in TEAMS:
            out[f"fluxo da equipe de {e}"] = [team_open[e], team_moves[e][0], comments_by_team[e], team_moves[e][1]]
        out["épicos"] = [epics[0], epics[1], epics_done]
        # ---------------------------------------------------------------- repository
        rev = dict(reviews)
        n_commits = sum(x[1] for x in commits)
        out["repositório de código"] = [n_commits, sum(x[2] for x in commits), rev.get("aprovou", 0), rev.get("pediu mudanças", 0),
                                        len(sis["repo"].branches)]
        cpc = {x[0]: x[1] for x in commits}
        tpc = {x[0]: (x[2], x[3]) for x in tests}
        for c in COMPONENTS:
            tt = tpc.get(c, (0, 0))
            out[f"código de {COMPONENT_NAME[c]}"] = [cpc.get(c, 0), tt[0] or 0, tt[1] or 0]
        # ---------------------------------------------------------------- CRM
        stage_counts, trans, activity_counts, tasks = sis["crm"].minute(t)
        by_stage = {}
        by_source = {o: 0 for o in SOURCES}
        value = 0.0
        for stage, origin, n, v in stage_counts:
            by_stage[stage] = by_stage.get(stage, 0) + n
            if stage in ("lead", "qualificação", "proposta", "negociação"):
                by_source[origin] = by_source.get(origin, 0) + n
                value += v
        won_count = sum(1 for _, src, dst in trans if dst == "ganho")
        lost = sum(1 for _, src, dst in trans if dst == "perdido")
        new_by_source = {o: 0 for o in SOURCES}
        for origin, src, dst in trans:
            if src is None and origin in new_by_source:
                new_by_source[origin] += 1
        out["funil de vendas"] = [by_stage.get("lead", 0), by_stage.get("qualificação", 0), by_stage.get("proposta", 0),
                                  by_stage.get("negociação", 0), won_count, lost, round(value / 1000.0, 1)]
        by_activity = dict(activity_counts)
        out["atividades de vendas"] = [by_activity.get("ligação", 0), by_activity.get("e-mail", 0), by_activity.get("proposta", 0), tasks]
        for o in SOURCES:
            out[f"leads de {o}"] = [new_by_source[o], by_source[o]]
        # ---------------------------------------------------------------- calendar and staff board
        company = m.company
        team_of = {}
        present_ids = set()
        present_count = {e: 0 for e in TEAMS}
        lunch = {e: 0 for e in TEAMS}
        headcount = {e: 0 for e in TEAMS}
        a = cal.absolute
        for p in company.people:
            if not p.active:
                continue
            team_of[p.id] = p.team
            headcount[p.team] += 1
            if p.present:
                present_ids.add(p.id)
                present_count[p.team] += 1
                if p.lunch_start <= a < p.lunch_end:
                    lunch[p.team] += 1
        agenda = sis["agenda"]
        in_meeting = {e: 0 for e in TEAMS}
        team_meetings = {e: 0 for e in TEAMS}
        by_type = {tp: [0, 0] for tp in MEETING_TYPES}
        counted = set()
        for begin, end, rid, kind, team, people in agenda.now:
            present_r = [x for x in people if x in present_ids]
            if not present_r:
                continue
            if team in team_meetings:
                team_meetings[team] += 1
            by_type[kind][0] += 1
            by_type[kind][1] += len(present_r)
            for x in present_r:
                if x not in counted:
                    counted.add(x)
                    in_meeting[team_of[x]] += 1
        for e in TEAMS:
            self.meeting_minutes[e] += in_meeting[e]
            out[f"agenda da equipe de {e}"] = [in_meeting[e], team_meetings[e], self.meeting_minutes[e]]
        for tp in MEETING_TYPES:
            out[f"reuniões do tipo {tp}"] = by_type[tp]
        q = sis["quadro"]
        for e in TEAMS:
            d = q.day[e]
            out[f"quadro da equipe de {e}"] = [headcount[e], present_count[e], lunch[e], d["férias"], d["falta"], round(d["extras"], 2)]
        openings, cand = q.opening_counts()
        out["quadro geral"] = [sum(headcount.values()), q.month["entradas"], q.month["saídas"], openings, cand, q.open_requests()]
        out["ponto"] = list(q.punches_min)
        q.punches_min = [0, 0]
        return {name: [float(v) for v in out[name]] for name, _ in self.processes}

