"""The company's workflow tracker (Jira-like), on a real database (SQLite). Projects (Produto, Plataforma, Suporte,
Infraestrutura), items with a type (epic, story, task, bug, ticket), per-type state, priority, component, owning team, points,
deadline, sprint, comments, item-version links, links between items (the ticket escalated to a bug, the bug caused by a story),
reopenings, and the log of every transition with instant and team. Two-week sprints per project, with planning (goal and capacity)
and a retrospective.

The actors here are the people (people.py) and the customers, through support. Counts per project, type, state, priority,
component and team are kept by the database itself (triggers), like the dashboard of such a system; the connectors only read
aggregates."""
import sqlite3

from .catalog import PROJECTS

STATES = {
    "épico": ("aberto", "em andamento", "concluído"),
    "história": ("backlog", "refinamento", "pronto para desenvolver", "em desenvolvimento", "em revisão", "em qualidade",
                 "pronto para liberar", "liberado"),
    "tarefa": ("backlog", "pronto para desenvolver", "em andamento", "em revisão", "pronto para liberar", "liberado", "concluído",
               "descartado"),
    "bug": ("aberto", "triagem", "pronto para desenvolver", "em desenvolvimento", "em revisão", "em qualidade", "pronto para liberar",
            "liberado", "não reproduzido"),
    "chamado": ("aberto", "em atendimento", "aguardando cliente", "escalado", "resolvido", "fechado", "descartado"),
}
FINAL_STATES = ("liberado", "concluído", "fechado", "descartado", "não reproduzido")
DELIVERED = ("liberado", "concluído", "resolvido", "fechado")
PRIORITIES = ("baixa", "média", "alta", "crítica")
FIRST_RESPONSE_SLA = {"crítica": 60, "alta": 240, "média": 1440, "baixa": 4320}     # minutes

SCHEMA = """
CREATE TABLE itens (id INTEGER PRIMARY KEY, chave TEXT, projeto TEXT, tipo TEXT, titulo TEXT, estado TEXT, prioridade TEXT,
    componente TEXT, equipe TEXT, responsavel INTEGER, sprint INTEGER, pontos INTEGER, prazo INTEGER, criado_em INTEGER,
    atualizado_em INTEGER, resolvido_em INTEGER, primeira_resposta_em INTEGER, cliente INTEGER, canal TEXT, versao TEXT,
    reaberto INTEGER DEFAULT 0, epico INTEGER, origem TEXT, protocolo INTEGER);
CREATE INDEX i_estado ON itens(projeto, tipo, estado);
CREATE INDEX i_sprint ON itens(sprint);
CREATE INDEX i_epico ON itens(epico);
CREATE INDEX i_protocolo ON itens(protocolo);
CREATE TABLE transicoes (id INTEGER PRIMARY KEY, item INTEGER, de TEXT, para TEXT, t INTEGER, equipe TEXT, reabertura INTEGER);
CREATE INDEX tr_t ON transicoes(t);
CREATE INDEX tr_item ON transicoes(item);
CREATE TABLE comentarios (id INTEGER PRIMARY KEY, item INTEGER, t INTEGER, equipe TEXT, texto TEXT);
CREATE INDEX co_t ON comentarios(t);
CREATE INDEX co_item ON comentarios(item);
CREATE TABLE sprints (id INTEGER PRIMARY KEY, projeto TEXT, numero INTEGER, inicio INTEGER, fim_previsto INTEGER,
    fechado_em INTEGER, meta_pontos INTEGER, capacidade_pontos INTEGER, meta TEXT, retrospectiva TEXT);
CREATE TABLE vinculos (item INTEGER, versao TEXT, tipo TEXT, t INTEGER);
CREATE TABLE ligacoes (de INTEGER, para INTEGER, tipo TEXT, t INTEGER);
CREATE INDEX l_de ON ligacoes(de);
CREATE INDEX l_para ON ligacoes(para);
CREATE TABLE contagens (projeto TEXT, tipo TEXT, estado TEXT, prioridade TEXT, componente TEXT, equipe TEXT, n INTEGER,
    soma_criado INTEGER, PRIMARY KEY (projeto, tipo, estado, prioridade, componente, equipe));
CREATE TRIGGER conta_novo AFTER INSERT ON itens BEGIN
    INSERT INTO contagens VALUES (NEW.projeto, NEW.tipo, NEW.estado, NEW.prioridade, COALESCE(NEW.componente, ''),
        COALESCE(NEW.equipe, ''), 1, NEW.criado_em)
    ON CONFLICT DO UPDATE SET n = n + 1, soma_criado = soma_criado + NEW.criado_em;
END;
CREATE TRIGGER conta_muda AFTER UPDATE OF estado, prioridade, componente, equipe ON itens BEGIN
    UPDATE contagens SET n = n - 1, soma_criado = soma_criado - OLD.criado_em
        WHERE projeto = OLD.projeto AND tipo = OLD.tipo AND estado = OLD.estado AND prioridade = OLD.prioridade
        AND componente = COALESCE(OLD.componente, '') AND equipe = COALESCE(OLD.equipe, '');
    INSERT INTO contagens VALUES (NEW.projeto, NEW.tipo, NEW.estado, NEW.prioridade, COALESCE(NEW.componente, ''),
        COALESCE(NEW.equipe, ''), 1, NEW.criado_em)
    ON CONFLICT DO UPDATE SET n = n + 1, soma_criado = soma_criado + NEW.criado_em;
END;
"""


class Workflow:
    def __init__(self):
        self.db = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.seq = {p: 0 for p in PROJECTS}

    # ---------- the API people use ----------
    def create(self, t, project, kind, title, priority="média", component=None, team=None, actor=None, points=None, deadline=None,
              customer=None, channel=None, epic=None, sprint=None, origin="equipe", protocol_no=None, state=None):
        self.seq[project] += 1
        key = f"{project}-{self.seq[project]}"
        state = state or STATES[kind][0]
        cur = self.db.execute(
            "INSERT INTO itens (chave, projeto, tipo, titulo, estado, prioridade, componente, equipe, sprint, pontos, prazo, criado_em, "
            "atualizado_em, cliente, canal, epico, origem, protocolo) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (key, project, kind, title, state, priority, component, team, sprint, points, deadline, t, t, customer, channel, epic,
             origin, protocol_no))
        self.db.execute("INSERT INTO transicoes (item, de, para, t, equipe, reabertura) VALUES (?,?,?,?,?,0)",
                        (cur.lastrowid, None, state, t, actor or team))
        return cur.lastrowid

    def transition(self, t, item, dst, actor, team=None):
        r = self.db.execute("SELECT estado, tipo, primeira_resposta_em FROM itens WHERE id=?", (item,)).fetchone()
        if r is None or r["estado"] == dst:
            return False
        if dst not in STATES[r["tipo"]]:
            raise ValueError(f"state {dst} does not exist for {r['tipo']}")
        src = r["estado"]
        reopening = 1 if (src in DELIVERED or src in FINAL_STATES) and dst not in DELIVERED and dst not in FINAL_STATES else 0
        resolved = t if dst in DELIVERED else None
        first = r["primeira_resposta_em"]
        if first is None and r["tipo"] == "chamado" and dst != "aberto":
            first = t
        self.db.execute("UPDATE itens SET estado=?, atualizado_em=?, resolvido_em=COALESCE(?, resolvido_em), reaberto=reaberto+?, "
                        "primeira_resposta_em=?, equipe=COALESCE(?, equipe) WHERE id=?",
                        (dst, t, resolved, reopening, first, team, item))
        self.db.execute("INSERT INTO transicoes (item, de, para, t, equipe, reabertura) VALUES (?,?,?,?,?,?)",
                        (item, src, dst, t, actor, reopening))
        return True

    def comment(self, t, item, team, text):
        self.db.execute("INSERT INTO comentarios (item, t, equipe, texto) VALUES (?,?,?,?)", (item, t, team, text))
        self.db.execute("UPDATE itens SET atualizado_em=? WHERE id=?", (t, item))

    def assign_to(self, item, person, team=None):
        if team is None:
            self.db.execute("UPDATE itens SET responsavel=? WHERE id=?", (person, item))
        else:
            self.db.execute("UPDATE itens SET responsavel=?, equipe=? WHERE id=?", (person, team, item))

    def set_priority(self, item, priority):
        self.db.execute("UPDATE itens SET prioridade=? WHERE id=?", (priority, item))

    def add_to_sprint(self, item, sprint):
        self.db.execute("UPDATE itens SET sprint=? WHERE id=?", (sprint, item))

    def estimate(self, item, points):
        self.db.execute("UPDATE itens SET pontos=? WHERE id=?", (points, item))

    def link_version(self, t, item, version, kind="corrigido em"):
        self.db.execute("INSERT INTO vinculos (item, versao, tipo, t) VALUES (?,?,?,?)", (item, version, kind, t))
        if kind == "corrigido em":
            self.db.execute("UPDATE itens SET versao=? WHERE id=?", (version, item))

    def connect(self, t, src, dst, kind):
        self.db.execute("INSERT INTO ligacoes (de, para, tipo, t) VALUES (?,?,?,?)", (src, dst, kind, t))

    # ---------- sprints ----------
    def open_sprint(self, t, project, number, planned_end, goal_points, capacity, goal):
        cur = self.db.execute("INSERT INTO sprints (projeto, numero, inicio, fim_previsto, meta_pontos, capacidade_pontos, meta) "
                              "VALUES (?,?,?,?,?,?,?)", (project, number, t, planned_end, goal_points, capacity, goal))
        return cur.lastrowid

    def close_sprint(self, t, sprint, retrospective):
        self.db.execute("UPDATE sprints SET fechado_em=?, retrospectiva=? WHERE id=?", (t, retrospective, sprint))

    def current_sprint(self, project):
        r = self.db.execute("SELECT * FROM sprints WHERE projeto=? AND fechado_em IS NULL ORDER BY id DESC LIMIT 1", (project,)).fetchone()
        return r

    def sprint_points(self, sprint):
        r = self.db.execute("SELECT COALESCE(SUM(pontos), 0) AS total, COALESCE(SUM(CASE WHEN estado IN ('liberado', 'concluído', "
                            "'pronto para liberar', 'não reproduzido') THEN pontos ELSE 0 END), 0) AS feitos, COUNT(*) AS n "
                            "FROM itens WHERE sprint=?", (sprint,)).fetchone()
        return r["total"], r["feitos"], r["n"]

    # ---------- queries ----------
    def item(self, item):
        return self.db.execute("SELECT * FROM itens WHERE id=?", (item,)).fetchone()

    def items(self, project=None, kind=None, states=None, sprint=None, assignee=-1, component=None, order_by="id", limit=None,
              extra=""):
        q = "SELECT * FROM itens WHERE 1=1"
        a = []
        if project:
            q += " AND projeto=?"
            a.append(project)
        if kind:
            if isinstance(kind, str):
                q += " AND tipo=?"
                a.append(kind)
            else:
                q += " AND tipo IN (%s)" % ",".join("?" * len(kind))
                a += list(kind)
        if states:
            q += " AND estado IN (%s)" % ",".join("?" * len(states))
            a += list(states)
        if sprint is not None:
            q += " AND sprint=?"
            a.append(sprint)
        if assignee is None:
            q += " AND responsavel IS NULL"
        elif assignee != -1:
            q += " AND responsavel=?"
            a.append(assignee)
        if component:
            q += " AND componente=?"
            a.append(component)
        q += extra + " ORDER BY " + order_by + (f" LIMIT {int(limit)}" if limit else "")
        return self.db.execute(q, a).fetchall()

    def count(self, project=None, kind=None, states=None, component=None):
        q = "SELECT COALESCE(SUM(n), 0) FROM contagens WHERE 1=1"
        a = []
        if project:
            q += " AND projeto=?"
            a.append(project)
        if kind:
            q += " AND tipo=?"
            a.append(kind)
        if states:
            q += " AND estado IN (%s)" % ",".join("?" * len(states))
            a += list(states)
        if component:
            q += " AND componente=?"
            a.append(component)
        return self.db.execute(q, a).fetchone()[0]

    def links_from(self, item, kind):
        return [r[0] for r in self.db.execute("SELECT para FROM ligacoes WHERE de=? AND tipo=? ORDER BY para", (item, kind)).fetchall()]

    def links_to(self, item, kind):
        return [r[0] for r in self.db.execute("SELECT de FROM ligacoes WHERE para=? AND tipo=? ORDER BY de", (item, kind)).fetchall()]

    # ---------- the minute (for the connectors) ----------
    def minute(self, t):
        db = self.db
        counts = db.execute("SELECT projeto, tipo, estado, prioridade, componente, equipe, n, soma_criado FROM contagens WHERE n>0").fetchall()
        transitions = db.execute("SELECT i.projeto, i.tipo, i.componente, i.canal, tr.de, tr.para, tr.equipe, tr.reabertura "
                                "FROM transicoes tr JOIN itens i ON i.id = tr.item WHERE tr.t=?", (t,)).fetchall()
        comments = db.execute("SELECT i.projeto, c.equipe, COUNT(*) FROM comentarios c JOIN itens i ON i.id = c.item WHERE c.t=? "
                                 "GROUP BY i.projeto, c.equipe", (t,)).fetchall()
        sprints = db.execute("SELECT s.projeto, s.meta_pontos, COALESCE(SUM(i.pontos), 0), COALESCE(SUM(CASE WHEN i.estado IN "
                             "('liberado', 'concluído', 'pronto para liberar', 'não reproduzido') THEN i.pontos ELSE 0 END), 0), "
                             "COUNT(i.id), COALESCE(SUM(CASE WHEN i.prioridade IN ('alta', 'crítica') THEN 1 ELSE 0 END), 0) "
                             "FROM sprints s LEFT JOIN itens i ON i.sprint = s.id WHERE s.fechado_em IS NULL GROUP BY s.id").fetchall()
        awaiting_first = db.execute("SELECT prioridade, criado_em FROM itens WHERE projeto='SUP' AND tipo='chamado' AND estado='aberto'").fetchall()
        return counts, transitions, comments, sprints, awaiting_first

    def __getstate__(self):
        d = dict(self.__dict__)
        d["db"] = None
        return d

    def attach_db(self, con):
        con.row_factory = sqlite3.Row
        self.db = con
