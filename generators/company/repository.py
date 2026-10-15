"""The product version repository (git-like), in SQLite. The main branch holds the implementation chosen for each function of the
code; each item under development has its own branch with the changes its commits made; quality approves and the branch is merged
into main; operations builds a version from main (or, for an urgent fix, from the live version plus the fix) and deploys it. Every
test run is also recorded here."""
import json
import sqlite3

from . import codebase

SCHEMA = """
CREATE TABLE commits (id INTEGER PRIMARY KEY, t INTEGER, item INTEGER, componente TEXT, funcao TEXT, de TEXT, para TEXT,
    linhas INTEGER, equipe TEXT, mensagem TEXT);
CREATE INDEX c_t ON commits(t);
CREATE TABLE versoes (id INTEGER PRIMARY KEY, nome TEXT, t INTEGER, codigo TEXT, origem TEXT, commits INTEGER, itens INTEGER);
CREATE TABLE implantacoes (id INTEGER PRIMARY KEY, t INTEGER, versao TEXT, tipo TEXT, commits INTEGER, itens INTEGER, equipe TEXT);
CREATE INDEX im_t ON implantacoes(t);
CREATE TABLE execucoes_teste (id INTEGER PRIMARY KEY, t INTEGER, componente TEXT, alvo TEXT, testes INTEGER, falhas INTEGER, equipe TEXT);
CREATE INDEX et_t ON execucoes_teste(t);
CREATE TABLE revisoes (id INTEGER PRIMARY KEY, t INTEGER, item INTEGER, resultado TEXT);
CREATE INDEX rv_t ON revisoes(t);
"""


class Repository:
    def __init__(self):
        self.db = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False)
        self.db.executescript(SCHEMA)
        self.main_branch = dict(codebase.INITIAL)
        self.sound = dict(codebase.INITIAL)          # the sound implementation of each function, which moves forward with the features
        self.authorship = {}                            # function -> item that put the current implementation into main
        self.branches = {}                              # item -> {function: implementation}
        self.branch_commits = {}                       # item -> number of commits
        self.pending_deploy = [0, 0]          # commits and items merged into main since the last version
        self.n_versions = 0
        self.versions = {"1.0": dict(codebase.INITIAL)}
        self.live = "1.0"
        self.previous = "1.0"
        self.db.execute("INSERT INTO versoes (nome, t, codigo, origem, commits, itens) VALUES (?,?,?,?,?,?)",
                        ("1.0", 0, json.dumps(codebase.INITIAL, sort_keys=True), "inicial", 0, 0))

    # ---------- commits ----------
    def commit(self, t, item, component, changes, rows, team, message):
        branch = self.branches.setdefault(item, {})
        if not changes:
            self.db.execute("INSERT INTO commits (t, item, componente, funcao, de, para, linhas, equipe, mensagem) VALUES (?,?,?,?,?,?,?,?,?)",
                            (t, item, component, None, None, None, rows, team, message))
        for func_name, impl in changes.items():
            src = branch.get(func_name, self.main_branch[func_name])
            branch[func_name] = impl
            self.db.execute("INSERT INTO commits (t, item, componente, funcao, de, para, linhas, equipe, mensagem) VALUES (?,?,?,?,?,?,?,?,?)",
                            (t, item, component, func_name, src, impl, rows, team, message))
        self.branch_commits[item] = self.branch_commits.get(item, 0) + max(1, len(changes))

    def branch_code(self, item):
        cod = dict(self.main_branch)
        cod.update(self.branches.get(item, {}))
        return cod

    def merge(self, item):
        """Merge the approved branch into main. Return the functions that changed."""
        branch = self.branches.pop(item, {})
        n = self.branch_commits.pop(item, 0)
        changed = []
        for func_name, impl in branch.items():
            if self.main_branch[func_name] != impl:
                changed.append(func_name)
            self.main_branch[func_name] = impl
            self.authorship[func_name] = item
            if (func_name, impl) not in codebase.DEFECTS:
                self.sound[func_name] = impl
        self.pending_deploy[0] += n
        self.pending_deploy[1] += 1
        return changed

    def discard_branch(self, item):
        self.branches.pop(item, None)
        self.branch_commits.pop(item, None)

    # ---------- versions and deployments ----------
    def build_version(self, t, base, origin):
        self.n_versions += 1
        name = f"1.{self.n_versions}"
        commits, items = self.pending_deploy if origin == "regular" else (1, 1)
        self.versions[name] = dict(base)
        self.db.execute("INSERT INTO versoes (nome, t, codigo, origem, commits, itens) VALUES (?,?,?,?,?,?)",
                        (name, t, json.dumps(base, sort_keys=True), origin, commits, items))
        if origin == "regular":
            self.pending_deploy = [0, 0]
        return name

    def record_deployment(self, t, version, kind, team):
        row = self.db.execute("SELECT commits, itens FROM versoes WHERE nome=?", (version,)).fetchone()
        commits, items = (row if row else (0, 0)) if kind != "reversão" else (0, 0)
        self.db.execute("INSERT INTO implantacoes (t, versao, tipo, commits, itens, equipe) VALUES (?,?,?,?,?,?)",
                        (t, version, kind, commits, items, team))
        self.previous = self.live
        self.live = version

    def record_tests(self, t, component, target, tests, failures, team):
        self.db.execute("INSERT INTO execucoes_teste (t, componente, alvo, testes, falhas, equipe) VALUES (?,?,?,?,?,?)",
                        (t, component, target, tests, failures, team))

    def record_review(self, t, item, result):
        self.db.execute("INSERT INTO revisoes (t, item, resultado) VALUES (?,?,?)", (t, item, result))

    def defects_in(self, cod):
        """For the ground truth: the defects present in a code map (function, implementation)."""
        return sorted((f, v) for f, v in cod.items() if (f, v) in codebase.DEFECTS)

    # ---------- the minute (for the connectors) ----------
    def minute(self, t):
        db = self.db
        commits = db.execute("SELECT componente, COUNT(*), COALESCE(SUM(linhas), 0) FROM commits WHERE t=? GROUP BY componente", (t,)).fetchall()
        tests = db.execute("SELECT componente, COUNT(*), SUM(testes), SUM(falhas) FROM execucoes_teste WHERE t=? GROUP BY componente", (t,)).fetchall()
        reviews = db.execute("SELECT resultado, COUNT(*) FROM revisoes WHERE t=? GROUP BY resultado", (t,)).fetchall()
        impl = db.execute("SELECT COUNT(*), COALESCE(SUM(commits), 0), COALESCE(SUM(itens), 0) FROM implantacoes WHERE t=?", (t,)).fetchone()
        return commits, tests, reviews, impl

    def __getstate__(self):
        d = dict(self.__dict__)
        d["db"] = None
        return d
