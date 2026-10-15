"""The sales team's own CRM, in SQLite: deals that go through lead, qualification, proposal and negotiation and end won or lost;
activities (call, e-mail, meeting, proposal sent); and the team's internal tasks (what the rest of the company asks of sales).
Leads come from the website, from customer referrals and from the team's own prospecting."""
import sqlite3

STAGES = ("lead", "qualificação", "proposta", "negociação", "ganho", "perdido")
OPEN_STAGES = ("lead", "qualificação", "proposta", "negociação")
SOURCES = ("site", "indicação", "prospecção")

SCHEMA = """
CREATE TABLE negocios (id INTEGER PRIMARY KEY, origem TEXT, estagio TEXT, plano TEXT, valor REAL, criado_em INTEGER,
    atualizado_em INTEGER, proxima_acao_em INTEGER, tentativas INTEGER, responsavel INTEGER, compromisso INTEGER, fechado_em INTEGER);
CREATE INDEX n_e ON negocios(estagio, proxima_acao_em);
CREATE TABLE atividades (id INTEGER PRIMARY KEY, negocio INTEGER, tipo TEXT, t INTEGER);
CREATE INDEX a_t ON atividades(t);
CREATE TABLE transicoes (id INTEGER PRIMARY KEY, negocio INTEGER, de TEXT, para TEXT, t INTEGER);
CREATE INDEX tc_t ON transicoes(t);
CREATE TABLE tarefas (id INTEGER PRIMARY KEY, texto TEXT, estado TEXT, criado_em INTEGER, concluido_em INTEGER, protocolo INTEGER);
CREATE INDEX ta_e ON tarefas(estado);
CREATE TABLE contagens (estagio TEXT, origem TEXT, n INTEGER, valor REAL, PRIMARY KEY (estagio, origem));
CREATE TRIGGER cn_novo AFTER INSERT ON negocios BEGIN
    INSERT INTO contagens VALUES (NEW.estagio, NEW.origem, 1, NEW.valor) ON CONFLICT DO UPDATE SET n = n + 1, valor = valor + NEW.valor;
END;
CREATE TRIGGER cn_muda AFTER UPDATE OF estagio ON negocios BEGIN
    UPDATE contagens SET n = n - 1, valor = valor - OLD.valor WHERE estagio = OLD.estagio AND origem = OLD.origem;
    INSERT INTO contagens VALUES (NEW.estagio, NEW.origem, 1, NEW.valor) ON CONFLICT DO UPDATE SET n = n + 1, valor = valor + NEW.valor;
END;
"""


class CRM:
    def __init__(self):
        self.db = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
        self.db.executescript(SCHEMA)
        self.db.row_factory = sqlite3.Row

    def new_deal(self, t, origin, plan, value, stage="lead", next_at=None, commitment=0):
        cur = self.db.execute("INSERT INTO negocios (origem, estagio, plano, valor, criado_em, atualizado_em, proxima_acao_em, "
                              "tentativas, compromisso) VALUES (?,?,?,?,?,?,?,0,?)",
                              (origin, stage, plan, value, t, t, t if next_at is None else next_at, commitment))
        self.db.execute("INSERT INTO transicoes (negocio, de, para, t) VALUES (?,?,?,?)", (cur.lastrowid, None, stage, t))
        return cur.lastrowid

    def move(self, t, deal, dst, next_at=None):
        src = self.db.execute("SELECT estagio FROM negocios WHERE id=?", (deal,)).fetchone()[0]
        if src == dst:
            return
        closed = t if dst in ("ganho", "perdido") else None
        self.db.execute("UPDATE negocios SET estagio=?, atualizado_em=?, proxima_acao_em=COALESCE(?, proxima_acao_em), tentativas=0, "
                        "fechado_em=COALESCE(?, fechado_em) WHERE id=?", (dst, t, next_at, closed, deal))
        self.db.execute("INSERT INTO transicoes (negocio, de, para, t) VALUES (?,?,?,?)", (deal, src, dst, t))

    def postpone(self, t, deal, next_at):
        self.db.execute("UPDATE negocios SET proxima_acao_em=?, tentativas=tentativas+1, atualizado_em=? WHERE id=?", (next_at, t, deal))

    def log_activity(self, t, deal, kind):
        self.db.execute("INSERT INTO atividades (negocio, tipo, t) VALUES (?,?,?)", (deal, kind, t))

    def assign(self, deal, person):
        self.db.execute("UPDATE negocios SET responsavel=? WHERE id=?", (person, deal))

    def next_due(self, t, stages, assignee=None):
        q = "SELECT * FROM negocios WHERE estagio IN (%s) AND proxima_acao_em<=?" % ",".join("?" * len(stages))
        a = list(stages) + [t]
        if assignee is not None:
            q += " AND (responsavel IS NULL OR responsavel=?)"
            a.append(assignee)
        q += " ORDER BY proxima_acao_em, id LIMIT 1"
        return self.db.execute(q, a).fetchone()

    def deal(self, deal):
        return self.db.execute("SELECT * FROM negocios WHERE id=?", (deal,)).fetchone()

    def count_in_stage(self, stage):
        return self.db.execute("SELECT COALESCE(SUM(n), 0) FROM contagens WHERE estagio=?", (stage,)).fetchone()[0]

    def open_count(self):
        return self.db.execute("SELECT COALESCE(SUM(n), 0), COALESCE(SUM(valor), 0) FROM contagens WHERE estagio IN "
                               "('lead', 'qualificação', 'proposta', 'negociação')").fetchone()

    # ---------- internal tasks ----------
    def new_task(self, t, text, protocol_no=None):
        return self.db.execute("INSERT INTO tarefas (texto, estado, criado_em, protocolo) VALUES (?,?,?,?)",
                               (text, "aberta", t, protocol_no)).lastrowid

    def open_task(self):
        return self.db.execute("SELECT * FROM tarefas WHERE estado='aberta' ORDER BY id LIMIT 1").fetchone()

    def close_task(self, t, task, state="concluída"):
        self.db.execute("UPDATE tarefas SET estado=?, concluido_em=? WHERE id=?", (state, t, task))

    # ---------- the minute ----------
    def minute(self, t):
        db = self.db
        counts = db.execute("SELECT estagio, origem, n, valor FROM contagens WHERE n>0").fetchall()
        transitions = db.execute("SELECT n.origem, tr.de, tr.para FROM transicoes tr JOIN negocios n ON n.id = tr.negocio WHERE tr.t=?", (t,)).fetchall()
        activities = db.execute("SELECT tipo, COUNT(*) FROM atividades WHERE t=? GROUP BY tipo", (t,)).fetchall()
        tasks = db.execute("SELECT COUNT(*) FROM tarefas WHERE estado='aberta'").fetchone()[0]
        return counts, transitions, activities, tasks

    def __getstate__(self):
        d = dict(self.__dict__)
        d["db"] = None
        return d

    def attach_db(self, con):
        con.row_factory = sqlite3.Row
        self.db = con
