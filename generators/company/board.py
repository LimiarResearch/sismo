"""The staff board, in SQLite: who is in the company and in which team, the time clock (recorded entries and exits), the day's
absences (vacation, sick leave), overtime, open positions and candidates, people joining and leaving. It also keeps the requests
sent to management (customer cancellations, internal requests). Aggregates are reported per team."""
import sqlite3

from .catalog import TEAMS

SCHEMA = """
CREATE TABLE pessoas (id INTEGER PRIMARY KEY, equipe TEXT, papel TEXT, projeto TEXT, entrada_em INTEGER, saida_em INTEGER, ativo INTEGER);
CREATE TABLE ponto (pessoa INTEGER, t INTEGER, tipo TEXT);
CREATE INDEX po_t ON ponto(t);
CREATE TABLE ausencias (pessoa INTEGER, data INTEGER, motivo TEXT);
CREATE TABLE extras (pessoa INTEGER, data INTEGER, minutos INTEGER);
CREATE TABLE vagas (id INTEGER PRIMARY KEY, equipe TEXT, papel TEXT, projeto TEXT, aberta_em INTEGER, fechada_em INTEGER, estado TEXT, motivo TEXT);
CREATE TABLE candidatos (id INTEGER PRIMARY KEY, vaga INTEGER, estagio TEXT, t INTEGER, nota REAL);
CREATE TABLE solicitacoes (id INTEGER PRIMARY KEY, t INTEGER, tipo TEXT, texto TEXT, estado TEXT, protocolo INTEGER, cliente INTEGER,
    concluida_em INTEGER);
CREATE INDEX so_e ON solicitacoes(estado);
"""


class StaffBoard:
    def __init__(self):
        self.db = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
        self.db.executescript(SCHEMA)
        self.punches_min = [0, 0]                           # entries and exits recorded in the minute
        self.day = {e: {"férias": 0, "falta": 0, "extras": 0.0} for e in TEAMS}
        self.month = {"entradas": 0, "saídas": 0, "mes": 0}

    def admit(self, t, person, team, role, project):
        self.db.execute("INSERT INTO pessoas (id, equipe, papel, projeto, entrada_em, ativo) VALUES (?,?,?,?,?,1)",
                        (person, team, role, project, t))

    def dismiss(self, t, person):
        self.db.execute("UPDATE pessoas SET ativo=0, saida_em=? WHERE id=?", (t, person))

    def punch_clock(self, t, person, kind):
        self.db.execute("INSERT INTO ponto (pessoa, t, tipo) VALUES (?,?,?)", (person, t, kind))
        self.punches_min[0 if kind == "entrada" else 1] += 1

    def log_absence(self, person, team, date, reason):
        self.db.execute("INSERT INTO ausencias (pessoa, data, motivo) VALUES (?,?,?)", (person, date, reason))
        self.day[team][reason] += 1

    def log_overtime(self, person, team, date, minutes):
        self.db.execute("INSERT INTO extras (pessoa, data, minutos) VALUES (?,?,?)", (person, date, minutes))
        self.day[team]["extras"] += minutes / 60.0

    def new_day(self, cal):
        self.day = {e: {"férias": 0, "falta": 0, "extras": 0.0} for e in TEAMS}
        if cal.month != self.month["mes"]:
            self.month = {"entradas": 0, "saídas": 0, "mes": cal.month}

    # ---------- positions ----------
    def open_position(self, t, team, role, project, reason):
        return self.db.execute("INSERT INTO vagas (equipe, papel, projeto, aberta_em, estado, motivo) VALUES (?,?,?,?,?,?)",
                               (team, role, project, t, "aberta", reason)).lastrowid

    def active_openings(self):
        return self.db.execute("SELECT * FROM vagas WHERE estado IN ('aberta', 'em contratação') ORDER BY id").fetchall()

    def update_opening(self, t, opening, state):
        closed_at = t if state in ("preenchida", "cancelada") else None
        self.db.execute("UPDATE vagas SET estado=?, fechada_em=COALESCE(?, fechada_em) WHERE id=?", (state, closed_at, opening))

    def candidate(self, t, opening, stage, score):
        return self.db.execute("INSERT INTO candidatos (vaga, estagio, t, nota) VALUES (?,?,?,?)", (opening, stage, t, score)).lastrowid

    def move_candidate(self, t, candidate, stage):
        self.db.execute("UPDATE candidatos SET estagio=?, t=? WHERE id=?", (stage, t, candidate))

    def candidates(self, opening, stage):
        return self.db.execute("SELECT * FROM candidatos WHERE vaga=? AND estagio=? ORDER BY id", (opening, stage)).fetchall()

    # ---------- requests to management ----------
    def request(self, t, kind, text, protocol_no=None, customer=None):
        return self.db.execute("INSERT INTO solicitacoes (t, tipo, texto, estado, protocolo, cliente) VALUES (?,?,?,?,?,?)",
                               (t, kind, text, "aberta", protocol_no, customer)).lastrowid

    def next_request(self, t, kinds=None):
        if kinds:
            return self.db.execute("SELECT * FROM solicitacoes WHERE estado='aberta' AND t<=? AND tipo IN (%s) ORDER BY id LIMIT 1"
                                   % ",".join("?" * len(kinds)), [t] + list(kinds)).fetchone()
        return self.db.execute("SELECT * FROM solicitacoes WHERE estado='aberta' AND t<=? ORDER BY id LIMIT 1", (t,)).fetchone()

    def complete_request(self, t, sid, state="concluída"):
        self.db.execute("UPDATE solicitacoes SET estado=?, concluida_em=? WHERE id=?", (state, t, sid))

    def open_requests(self):
        return self.db.execute("SELECT COUNT(*) FROM solicitacoes WHERE estado='aberta'").fetchone()[0]

    def opening_counts(self):
        v = self.db.execute("SELECT COUNT(*) FROM vagas WHERE estado IN ('aberta', 'em contratação')").fetchone()[0]
        c = self.db.execute("SELECT COUNT(*) FROM candidatos WHERE estagio IN ('triagem', 'entrevista', 'proposta')").fetchone()[0]
        return v, c

    def __getstate__(self):
        d = dict(self.__dict__)
        d["db"] = None
        return d
