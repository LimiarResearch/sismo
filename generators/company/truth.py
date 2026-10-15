"""The ground truth: what the company has and when it happened, so the benchmark can score what a detector reports. Nothing here
is read by the people or by the systems, and nothing goes out through the world interface: the mechanisms only record what they
did.

What is recorded:
- cycles: the calendar laws (workday, busier Monday, slower Friday, releases on Tuesdays and Thursdays, end of sprint, end of
  month) and the instants at which each sprint end and month end fell; in the shuffled null variant, the drawn calendar blocks;
- releases: every deployment, with the defects that went live and left, and the features that came with it;
- defect episodes: for each defect that reached production, the release, the first error, the first ticket it caused, the first
  escalation, and the fix (or rollback) that took it out;
- incidents: when the product stopped responding, why, when it came back, how many tickets it caused;
- regime changes: the releases that permanently changed the work of a route (the new version), with latency before and after;
- drift: the customer base day by day and the weekly growth rate;
- sprints: goal, capacity and their ratio (a rush sprint is one planned above capacity), and the defects written during it;
- staff: hires and departures;
- acts received through the interface and their responses."""
from . import codebase
from .catalog import ROUTES, MINUTES_PER_DAY


class Truth:
    def __init__(self, seed, null):
        self.seed = seed
        self.null = null
        self.releases = []
        self.episodes = []                 # live defects
        self.live = {}                     # (function, implementation) -> open episode
        self.defects_written = []
        self.defects_blocked = []
        self.incidents = []
        self.open_incident = None
        self.regimes = []
        self.portfolio = []
        self.portfolio_events = []
        self.sprints = []
        self.staff = []
        self.sprint_ends = []
        self.month_ends = []
        self.acts = {}
        self.daily_latency = {r: [] for r in ROUTES}     # (day, mean latency during business hours)
        self._lat = {r: [0.0, 0] for r in ROUTES}
        self.process_crash_errors = []
        self.crashes = []
        self._going_down = None
        self.tickets_by_cause = {"defeito": 0, "incidente": 0, "queda do processo": 0, "outros": 0}

    # ---------- live code ----------
    def deployment(self, t, version, kind, before, after, features, product):
        entering = sorted((f, v) for f, v in after.items() if (f, v) in codebase.DEFECTS and before.get(f) != v)
        leaving = sorted((f, v) for f, v in before.items() if (f, v) in codebase.DEFECTS and after.get(f) != v)
        regime = []
        for f, v in sorted(after.items()):
            if before.get(f) != v and (f, v) not in codebase.DEFECTS and (f, before.get(f)) not in codebase.DEFECTS:
                regime.append(f)
        self.releases.append({"t": t, "versao": version, "tipo": kind,
                                "defeitos_que_entraram": [list(x) for x in entering], "defeitos_que_sairam": [list(x) for x in leaving],
                                "funcoes_que_mudaram_de_comportamento": regime})
        for f, v in leaving:
            ep = self.live.pop((f, v), None)
            if ep is not None:
                ep["saiu_do_ar"] = t
                ep["saiu_por"] = kind
        for f, v in entering:
            defect_kind, description = codebase.DEFECTS[(f, v)]
            ep = {"funcao": f, "implementacao": v, "componente": codebase.FUNCTION_COMPONENT[f], "como_aparece": defect_kind,
                  "descricao": description, "liberado_em": t, "versao": version, "primeiro_erro": None, "erros": 0,
                  "primeiro_chamado": None, "chamados": 0, "primeira_escalacao": None, "escalacoes": 0, "saiu_do_ar": None,
                  "saiu_por": None}
            self.episodes.append(ep)
            self.live[(f, v)] = ep
        for f in regime:
            routes = sorted({r for r, fs in ROUTE_FUNCTIONS.items() if f in fs})
            self.regimes.append({"t": t, "versao": version, "funcao": f, "de": before.get(f), "para": after[f], "rotas": routes,
                                 "tipo": "mudança de regime"})

    def minute_errors(self, t, errors):
        """The product errors in this minute (route, function where the error was raised, exception type)."""
        for _, route, func_name, kind in errors:
            if func_name is None:
                continue
            for (f, v), ep in self.live.items():
                if f == func_name:
                    ep["erros"] += 1
                    if ep["primeiro_erro"] is None:
                        ep["primeiro_erro"] = t
            if route == "processo" and self._going_down is None:
                self.process_crash_errors.append(t)

    def defect_written(self, t, item, project, func_name, impl, haste):
        self.defects_written.append({"t": t, "item": item, "projeto": project, "funcao": func_name, "implementacao": impl,
                                       "pressa_do_squad": round(haste, 2)})

    def defect_blocked(self, t, item, func_name, by):
        self.defects_blocked.append({"t": t, "item": item, "funcao": func_name, "por": by})

    # ---------- tickets ----------
    def ticket_opened(self, t, item, customer, reason, comp, cause):
        func_name = cause[0] if cause else None
        when = cause[1] if cause else None
        match = None
        if func_name is not None:
            for (f, v), ep in list(self.live.items()) + [((e["funcao"], e["implementacao"]), e) for e in self.episodes
                                                          if e["saiu_do_ar"] is not None and when is not None
                                                          and e["liberado_em"] <= when <= e["saiu_do_ar"]]:
                if f == func_name:
                    match = ep
                    break
        if match is not None:
            match["chamados"] += 1
            if match["primeiro_chamado"] is None:
                match["primeiro_chamado"] = t
            self.tickets_by_cause["defeito"] += 1
            self._ticket_cause(item, match)
            return
        inc = self.open_incident or (self.incidents[-1] if self.incidents else None)
        if inc is not None and inc["causa"] != "volume do banco cheio":
            inc = self.incidents[-1] if self.incidents else None
        if reason in ("erro", "lentidão") and inc is not None and when is not None and inc["inicio"] <= when <= (inc["fim"] or t):
            inc["chamados"] += 1
            if inc["primeiro_chamado"] is None:
                inc["primeiro_chamado"] = t
            self.tickets_by_cause["incidente"] += 1
            self._ticket_cause(item, inc)
            return
        self.tickets_by_cause["outros"] += 1

    def _ticket_cause(self, item, ep):
        self._causes = getattr(self, "_causes", {})
        self._causes[item] = ep

    def escalated(self, t, ticket, dest):
        ep = getattr(self, "_causes", {}).get(ticket)
        if ep is not None:
            ep["escalacoes"] = ep.get("escalacoes", 0) + 1
            if ep.get("primeira_escalacao") is None:
                ep["primeira_escalacao"] = t

    # ---------- product down ----------
    def probe_minute(self, t, failing, product):
        if failing and self.open_incident is None:
            free = product.volume_pages - product.pages_in_use()
            self.open_incident = {"inicio": t, "fim": None, "causa": "volume do banco cheio" if free < 200 else "processo parado",
                                     "primeiro_chamado": None, "chamados": 0, "primeira_escalacao": None, "escalacoes": 0,
                                     "folga_dada_em_dias": None, "registros_apagados": None}
            if self.open_incident["causa"] == "volume do banco cheio":
                self.incidents.append(self.open_incident)
            else:
                self.crashes.append(self.open_incident)        # the short process crash for lack of memory (a live defect)
        elif not failing and self.open_incident is not None:
            self.open_incident["fim"] = t
            self.open_incident["duracao_min"] = t - self.open_incident["inicio"]
            self.open_incident = None

    def incident_resolved(self, t, cause, headroom, deleted):
        inc = self.open_incident or (self.incidents[-1] if self.incidents else None)
        if inc is not None:
            inc["causa_diagnosticada"] = cause
            inc["folga_dada_em_dias"] = headroom
            inc["registros_apagados"] = deleted

    # ---------- calendar ----------
    def new_date(self, t, cal):
        if cal.day_of_month == cal.days_in_month and not self.null == "embaralhado":
            self.month_ends.append(t)

    def lived_day(self, t, portfolio):
        self.portfolio.append((t, portfolio))

    def record_latency(self, t, cal, routes):
        if cal.workday and 9 * 60 <= cal.minute < 18 * 60:
            for r, v in routes.items():
                if v[0] > 0:
                    acc = self._lat[r]
                    acc[0] += v[3]
                    acc[1] += 1
        if cal.minute == MINUTES_PER_DAY - 1:
            for r in ROUTES:
                acc = self._lat[r]
                if acc[1]:
                    self.daily_latency[r].append((t // MINUTES_PER_DAY, round(acc[0] / acc[1], 1)))
                self._lat[r] = [0.0, 0]

    # ---------- sprints, staff, customer base, acts ----------
    def sprint_planned(self, t, project, number, goal, capacity, ratio, cal):
        self.sprints.append({"projeto": project, "numero": number, "inicio": t, "meta_pontos": goal, "capacidade_pontos": capacity,
                             "meta_sobre_capacidade": round(ratio, 2), "pressa": ratio > 1.15, "fim": None, "pontos_feitos": None})

    def sprint_closed(self, t, project, number, total, done_points):
        for s in self.sprints:
            if s["projeto"] == project and s["numero"] == number:
                s["fim"] = t
                s["pontos_feitos"] = done_points
        self.sprint_ends.append({"t": t, "projeto": project, "numero": number})

    def staff_event(self, t, kind, team):
        self.staff.append({"t": t, "tipo": kind, "equipe": team})

    def portfolio_event(self, t, kind, customer, plan):
        self.portfolio_events.append((t, kind, plan))

    def act(self, t, number, team, kind):
        self.acts[number] = {"recebido": t, "equipe": team, "tipo": kind, "respondido": None}

    def act_answered(self, t, number):
        if number in self.acts:
            self.acts[number]["respondido"] = t

    # ---------- what the benchmark reads ----------
    def as_dict(self, clock, shuffled):
        defects_live = [e for e in self.episodes]
        portfolio_series = self.portfolio
        weeks = []
        for i in range(7, len(portfolio_series), 7):
            a, b = portfolio_series[i - 7][1], portfolio_series[i][1]
            if a:
                weeks.append(round(100.0 * (b - a) / a, 2))
        regimes = []
        for r in self.regimes:
            d = r["t"] // MINUTES_PER_DAY
            before, after = [], []
            for route in r["rotas"]:
                series = self.daily_latency.get(route, [])
                a = [v for dd, v in series if d - 7 <= dd < d]
                b = [v for dd, v in series if d < dd <= d + 7]
                before.append(round(sum(a) / len(a), 1) if a else None)
                after.append(round(sum(b) / len(b), 1) if b else None)
            regimes.append(dict(r, latencia_media_7_dias_antes=before, latencia_media_7_dias_depois=after))
        cycles = {
            "dia_util": "as pessoas trabalham das 8h às 18h nos dias úteis; os clientes usam o produto no horário comercial deles, "
                        "com almoço mais vazio e picos às 10h e às 15h; tarefas agendadas do servidor rodam de madrugada (cópia às 2h, "
                        "limpeza de sessões às 3h, reposição de estoque às 4h, resumo às 7h)",
            "semana": "segunda-feira com mais uso e mais chamados (inclusive os guardados do fim de semana); sexta com menos uso e "
                      "gente saindo mais cedo; liberações às terças e quintas a partir das 15h; reindexação aos domingos 4h30",
            "sprint": "sprints de duas semanas que começam às segundas; planejamento no primeiro dia, revisão e retrospectiva na sexta "
                      "da segunda semana, liberação extra nessa sexta de manhã; a pressa cresce no fim quando o sprint está atrasado",
            "mes": "faturamento no dia 1 às 6h (fila de trabalhos cheia); reunião mensal no primeiro dia útil; vendas fecham mais "
                   "nos últimos seis dias do mês; as lojas tiram mais relatórios no fim do mês",
            "fins_de_sprint": self.sprint_ends,
            "fins_de_mes": self.month_ends,
        }
        if shuffled:
            cycles = {"ausentes": "nulo embaralhado: os processos vivem num calendário sorteado em blocos; nenhum ciclo de hora, de "
                                   "dia da semana, de sprint ou de mês corresponde ao relógio da porta",
                      "blocos_do_calendario": clock.blocks}
        output = {
            "semente": self.seed,
            "nulo": self.null,
            "minutos": clock.t,
            "convencao_do_tempo": "t = 0 é a criação (segunda-feira, 0h); cada passo avança t e faz acontecer o minuto t",
            "ciclos": cycles,
            "liberacoes": self.releases,
            "liberacoes_com_defeito": [l for l in self.releases if l["defeitos_que_entraram"]],
            "episodios_de_defeito_no_ar": defects_live,
            "incidentes": self.incidents,
            "mudancas_de_regime": regimes,
            "deriva": {"carteira_por_dia": self.portfolio, "crescimento_por_semana_em_porcento": weeks,
                       "entradas_e_saidas": self.portfolio_events},
            "sprints": self.sprints,
            "sprints_de_pressa": [s for s in self.sprints if s["pressa"]],
            "defeitos_escritos": self.defects_written,
            "defeitos_barrados_antes_do_ar": self.defects_blocked,
            "quedas_do_processo_por_memoria": {"erros_no_registro": self.process_crash_errors, "sonda_parada": self.crashes},
            "pessoal": self.staff or [],
            "chamados_por_causa": self.tickets_by_cause,
            "atos": self.acts,
        }
        if self.null == "sem_defeito":
            output["observacao_do_nulo"] = ("nenhuma liberação levou defeito ao ar; os episódios de erros seguidos de chamados nesse nulo "
                                           "são só os incidentes listados em 'incidentes'")
        if self.null == "sem_deriva":
            output["observacao_do_nulo"] = ("a carteira não cresce: cada cliente que entra leva à saída do cliente mais insatisfeito em até "
                                           "dois dias; a versão nova continua mudando a latência (está em 'mudancas_de_regime')")
        if self.null == "surdo":
            output["observacao_do_nulo"] = "a porta aceita atos e devolve números, mas nada acontece e nada é respondido"
        return output


def _route_functions():
    import inspect
    out = {}
    for route, f in codebase.ROUTE_HANDLERS.items():
        source = inspect.getsource(f)
        out[route] = {fn for fn in codebase.IMPLEMENTATIONS if f'cod["{fn}"]' in source}
    out["fila"] = {"emitir_nota", "enviar_email"}
    return out


ROUTE_FUNCTIONS = _route_functions()
