"""The company calendar, in SQLite: meetings with type, team, start, end and participants. Times are in company calendar time
(see clock.py). Whoever is in a running meeting does not act on the systems in that minute."""
import sqlite3

from .catalog import MINUTES_PER_DAY

TYPES = ("diária", "planejamento", "refinamento", "revisão e retrospectiva", "semanal", "liderança", "mensal", "com cliente",
         "entrevista", "alinhamento")
WORKDAY_START = 9 * 60
WORKDAY_END = 17 * 60 + 30

SCHEMA = """
CREATE TABLE reunioes (id INTEGER PRIMARY KEY, tipo TEXT, equipe TEXT, inicio INTEGER, fim INTEGER, titulo TEXT, origem TEXT,
    protocolo INTEGER, marcada_em INTEGER);
CREATE INDEX r_i ON reunioes(inicio);
CREATE TABLE participantes (reuniao INTEGER, pessoa INTEGER);
"""


class Agenda:
    def __init__(self):
        self.db = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
        self.db.executescript(SCHEMA)
        self.days = {}            # calendar date -> [(start, end, id, type, team, people)]
        self.created = {}          # date -> real instant at which the first meeting of that date was scheduled
        self.generated = set()      # dates whose fixed meetings are already on the calendar
        self.now = ()           # the meetings running in this minute
        self.busy = frozenset()

    def schedule(self, t, kind, team, start, duration, people, title, origin="rotina", protocol_no=None):
        people = tuple(sorted(set(people)))
        if not people:
            return None
        end = start + duration
        rid = self.db.execute("INSERT INTO reunioes (tipo, equipe, inicio, fim, titulo, origem, protocolo, marcada_em) VALUES (?,?,?,?,?,?,?,?)",
                              (kind, team, start, end, title, origin, protocol_no, t)).lastrowid
        self.db.executemany("INSERT INTO participantes (reuniao, pessoa) VALUES (?,?)", [(rid, p) for p in people])
        date = start // MINUTES_PER_DAY
        self.days.setdefault(date, []).append((start, end, rid, kind, team, people))
        self.created.setdefault(date, t)
        return rid

    def unschedule_person(self, person, from_t):
        """Remove the person from future meetings (when they leave the company)."""
        for date, entries in self.days.items():
            updated = []
            for r in entries:
                if r[0] >= from_t and person in r[5]:
                    r = r[:5] + (tuple(p for p in r[5] if p != person),)
                updated.append(r)
            self.days[date] = updated

    def minute(self, t, cal):
        """Update the running meetings and return the set of people in a meeting."""
        entries = self.days.get(cal.date, ())
        now = cal.absolute
        self.now = tuple(r for r in entries if r[0] <= now < r[1])
        if self.now:
            busy = set()
            for r in self.now:
                busy.update(r[5])
            self.busy = frozenset(busy)
        else:
            self.busy = frozenset()
        return self.busy

    def prune(self, t, cal, shuffled):
        for date in list(self.days):
            stale = (t - self.created.get(date, t) > 20 * MINUTES_PER_DAY) if shuffled else (date < cal.date - 1)
            if stale:
                del self.days[date]
                self.created.pop(date, None)

    def is_free(self, people, start, duration):
        end = start + duration
        ps = set(people)
        for r in self.days.get(start // MINUTES_PER_DAY, ()):
            if r[0] < end and start < r[1] and ps.intersection(r[5]):
                return False
        return True

    def first_free_slot(self, people, now_abs, duration, lead_time=30, days=6):
        """The first working-hours slot, on a workday, in which everyone is free. Searches in half-hour steps."""
        start = now_abs + lead_time
        start += (-start) % 30
        limit = now_abs + days * MINUTES_PER_DAY
        while start < limit:
            date, m = divmod(start, MINUTES_PER_DAY)
            if date % 7 >= 5 or m >= WORKDAY_END - duration:
                start = (date + 1) * MINUTES_PER_DAY + WORKDAY_START
                continue
            if m < WORKDAY_START:
                start = date * MINUTES_PER_DAY + WORKDAY_START
                continue
            if 12 * 60 <= m < 13 * 60 + 30:
                start = date * MINUTES_PER_DAY + 13 * 60 + 30
                continue
            if self.is_free(people, start, duration):
                return start
            start += 30
        return None

    def __getstate__(self):
        d = dict(self.__dict__)
        d["db"] = None
        return d
