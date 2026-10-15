"""The synthetic streams of the benchmark: 20,000 items, change at T = 10,000, warm-up of 2,000. Each stream returns
(X, y, expected, truth, numeric, K): X the fields, y the response, expected the kind of change ("REAL" = the relation between fields and
response breaks; "VIRTUAL" = the input changes; None = nothing changes), truth the fields that really changed, numeric, K the number of
classes. Each family keeps its own list of types, because the seed of each stream depends on the position of the type in that list.

Binary (relation y = rule of the fields):
  sea, sea_large, sea_gradual    y = x1 + x2 <= theta; theta 8 -> 9 (8 -> 10 in the large one); gradual: the new concept comes in
                                 over 2,000 items. REAL {0, 1}
  stagger                        the STAGGER rule 0 -> 1 (river). REAL {0, 1, 2}
  cov, cov_gradual               SEA without change; x2 goes from U[0,10] to U[4,10] (gradual: over 2,000 items). VIRTUAL {1}
  num_real                       20 numbers N(0,1); logit = 1.5 (x_a + x_b + x_c); at T the weight of x_a becomes -1.5. REAL {a}
  num_cov                        the same without a change in the relation; x_b becomes N(1,1). VIRTUAL {b}
  num_imbalanced, num_noisy      num_real with intercept -2.5 (about 20% positives); with 10% of the labels flipped
  cat_real                       20 categorical fields (3 values); y = random table of (c_a, c_b, c_c); at T c_c gives way to c_d.
                                 REAL {c, d}
  cat_cov                        the same rule without change; an irrelevant c_e starts falling 80% on a single value. VIRTUAL {e}
  null_sea, null_num, null_cat   no change
Several classes:
  mc_real   20 numbers, 4 classes by the largest of 4 linear scores in (a, b, c) with Gumbel noise; at T the weight of x_a flips. REAL {a}
  mc_cov    the same rule without change; x_b becomes N(1,1). VIRTUAL {b}
  mc_cat    20 categorical fields, 5 classes by a table of (c_a, c_b); at T c_b gives way to c_d. REAL {b, d}
  null_mc   mc_real without change
Slow drift (20 numbers, 4 classes by the rule of mc_real):
  null; slow_all (all 20 rise by 1 sd in a straight line along the stream; the relation does not change); slow_few (the same on 3
  irrelevant fields); slow_abrupt (slow_all and, at T, one irrelevant field jumps by 1 sd at once: VIRTUAL {e}); slow_real (slow_all
  and, at T, the weight of x_a flips: REAL {a}); ramp_all (no change until T; all 20 rise by 0.5 sd on a ramp of 2,000 items: VIRTUAL,
  all fields)
XOR (10 numbers; y = [x_a > 0] XOR [x_b > 0], 10% of the labels flipped; at T it becomes XNOR: the change is only in the combination):
  xor (REAL {a, b}), null_xor"""
import numpy as np
from river.datasets import synth

N, T, RAMP = 20000, 10000, 2000
# The order of each type list is part of the seeds: the seed of a stream uses the position of its type in the list.
BINARY_TYPES = ["sea", "sea_large", "sea_gradual", "stagger", "cov", "cov_gradual", "num_real", "num_cov", "num_imbalanced", "num_noisy",
                "cat_real", "cat_cov", "null_sea", "null_num", "null_cat"]


def _new(g, gradual):
    """For each item, whether it comes from the new concept."""
    t = np.arange(N)
    if not gradual:
        return t >= T
    return g.random(N) < np.clip((t - T) / RAMP, 0, 1)


def _binary(kind, s):
    g = np.random.default_rng(100000 + 97 * s + BINARY_TYPES.index(kind))
    if kind == "stagger":
        X, Y = [], []
        for i, f in enumerate((0, 1)):
            it = iter(synth.STAGGER(classification_function=f, seed=int(1_000_003 * s + i)))
            for _ in range(T):
                x, y = next(it); X.append([x["size"], x["color"], x["shape"]]); Y.append(int(y))
        return np.array(X, float), np.array(Y), "REAL", {0, 1, 2}, True
    if kind in ("sea", "sea_large", "sea_gradual", "cov", "cov_gradual", "null_sea"):
        X = g.uniform(0, 10, (N, 3))
        th = np.full(N, 8.0)
        if kind.startswith("sea"):
            th[_new(g, kind == "sea_gradual")] = 10.0 if kind == "sea_large" else 9.0
        if kind.startswith("cov"):
            m = _new(g, kind == "cov_gradual")
            X[m, 1] = g.uniform(4, 10, m.sum())
        y = (X[:, 0] + X[:, 1] <= th).astype(int)
        exp = {"sea": ("REAL", {0, 1}), "cov": ("VIRTUAL", {1}), "null": (None, set())}[kind.split("_")[0]]
        return X, y, exp[0], exp[1], True
    if kind.startswith("num") or kind == "null_num":
        X = g.normal(0, 1, (N, 20))
        a, b, c = g.choice(20, 3, replace=False)
        w = np.zeros((N, 20)); w[:, [a, b, c]] = 1.5
        if kind in ("num_real", "num_imbalanced", "num_noisy"):
            w[T:, a] = -1.5
        if kind == "num_cov":
            X[T:, b] += 1.0
        b0 = -2.5 if kind == "num_imbalanced" else 0.0
        y = (g.random(N) < 1 / (1 + np.exp(-((X * w).sum(1) + b0)))).astype(int)
        if kind == "num_noisy":
            flip = g.random(N) < 0.1; y[flip] = 1 - y[flip]
        if kind == "num_cov":
            return X, y, "VIRTUAL", {int(b)}, True
        if kind == "null_num":
            return X, y, None, set(), True
        return X, y, "REAL", {int(a)}, True
    # categorical
    X = g.integers(0, 3, (N, 20))
    a, b, c, d, e = g.choice(20, 5, replace=False)
    tab = g.integers(0, 2, (3, 3, 3))
    y = tab[X[:, a], X[:, b], X[:, c]]
    if kind == "cat_real":
        y[T:] = tab[X[T:, a], X[T:, b], X[T:, d]]
        return X, y, "REAL", {int(c), int(d)}, False
    if kind == "cat_cov":
        m = g.random(N - T) < 0.8
        X[T:, e][m] = 0                     # X[T:, e] is a view: this writes into X
        return X, y, "VIRTUAL", {int(e)}, False
    return X, y, None, set(), False


MC_TYPES = ["mc_real", "mc_cov", "mc_cat", "null_mc"]


def _multiclass(kind, s):
    g = np.random.default_rng(900000 + 97 * s + MC_TYPES.index(kind))
    if kind == "mc_cat":
        X = g.integers(0, 3, (N, 20))
        a, b, d = (int(v) for v in g.choice(20, 3, replace=False))
        tab = g.integers(0, 5, (3, 3))
        y = tab[X[:, a], X[:, b]]
        y[T:] = tab[X[T:, a], X[T:, d]]
        return X, y, "REAL", {b, d}, False, 5
    X = g.normal(0, 1, (N, 20))
    a, b, c = (int(v) for v in g.choice(20, 3, replace=False))
    Wt = g.normal(0, 1.5, (4, 3))
    score = np.stack([X[:, [a, b, c]] @ Wt[k] for k in range(4)], 1)
    if kind == "mc_real":
        score[T:] = np.stack([X[T:, [a, b, c]] @ (Wt[k] * np.array([-1, 1, 1])) for k in range(4)], 1)
    if kind == "mc_cov":
        X[T:, b] += 1.0
        score[T:] = np.stack([X[T:, [a, b, c]] @ Wt[k] for k in range(4)], 1)
    y = np.argmax(score + g.gumbel(size=score.shape), 1)
    if kind == "mc_real":
        return X, y, "REAL", {a}, True, 4
    if kind == "mc_cov":
        return X, y, "VIRTUAL", {b}, True, 4
    return X, y, None, set(), True, 4


K_SLOW = 4
SLOW_TYPES = ["null", "slow_all", "slow_few", "slow_abrupt", "slow_real", "ramp_all"]


def _slow(kind, s):
    g = np.random.default_rng(300000 + 211 * s + SLOW_TYPES.index(kind))
    X = g.normal(0, 1, (N, 20))
    a, b, c, e, f, h = (int(v) for v in g.choice(20, 6, replace=False))
    Wt = g.normal(0, 1.5, (K_SLOW, 3))
    t = np.arange(N)[:, None] / N
    if kind in ("slow_all", "slow_abrupt", "slow_real"):
        X += t
    if kind == "slow_few":
        X[:, [e, f, h]] += t
    if kind == "slow_abrupt":
        X[T:, e] += 1.0
    if kind == "ramp_all":
        X += 0.5 * np.clip((np.arange(N)[:, None] - T) / RAMP, 0, 1)
    score = X[:, [a, b, c]] @ Wt.T
    if kind == "slow_real":
        score[T:] = X[T:, [a, b, c]] @ (Wt * np.array([-1, 1, 1])).T
    y = np.argmax(score + g.gumbel(size=score.shape), 1)
    exp = {"slow_abrupt": ("VIRTUAL", {e}), "slow_real": ("REAL", {a}), "ramp_all": ("VIRTUAL", set(range(20)))}.get(kind, (None, set()))
    return X, y, exp[0], exp[1]


def _xor(kind, s):
    g = np.random.default_rng(700000 + 97 * s + XOR_TYPES.index(kind))
    X = g.normal(0, 1, (N, 10))
    a, b = (int(v) for v in g.choice(10, 2, replace=False))
    y = ((X[:, a] > 0) ^ (X[:, b] > 0)).astype(int)
    if kind == "xor":
        y[T:] = 1 - y[T:]
    flip = g.random(N) < 0.1
    y[flip] = 1 - y[flip]
    if kind == "xor":
        return X, y, "REAL", {a, b}, True
    return X, y, None, set(), True


XOR_TYPES = BINARY_TYPES + ["xor", "null_xor"]
ALL = BINARY_TYPES + MC_TYPES + ["slow_" + t if t == "null" else t for t in SLOW_TYPES] + ["xor", "null_xor"]


def stream(name, s):
    """(X, y, expected, truth, numeric, K) of the stream with this name and seed; the null of the slow family is called slow_null here."""
    if name in BINARY_TYPES:
        X, y, e, v, num = _binary(name, s); return X, y, e, v, num, 2
    if name in MC_TYPES:
        return _multiclass(name, s)
    if name in ("xor", "null_xor"):
        X, y, e, v, num = _xor(name, s); return X, y, e, v, num, 2
    t = "null" if name == "slow_null" else name
    X, y, e, v = _slow(t, s); return X, y, e, v, True, K_SLOW
