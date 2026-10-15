"""The evidence pieces of the detector.
Each field is split into bins; each bin is an indicator that fires when the value falls in it. For each bin, the input axis compares
how often it fires in the recent stretch with how often it fires in the reference (a two-sample Beta-Bernoulli Bayes factor that
includes the uncertainty of the reference itself); the relation axis compares, per bin and per class, how many times the class
appeared (observed) with how many the reference model expected (sum of the probabilities), in a Gamma-Poisson Bayes factor. A stretch
only grows once the reference of the bin has the minimum history (MIN_REFERENCE items); while the evidence of the stretch is not
positive, the stretch is folded back into the reference.
The decision looks at the mean of the e-values of all bins (averaging e-values, Shin, Ramdas and Rinaldo)."""
import math

import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln

MIN_REFERENCE = 176          # minimum reference history of a bin: ceil(sd^2 / alpha) with sd = 2


def _lg(x):
    return gammaln(x)


def lbeta(a, b):
    return gammaln(a) + gammaln(b) - gammaln(np.asarray(a) + np.asarray(b))


def log_mean_exp(lbf):
    """log of the mean of exp(lbf): the log of the mean e-value."""
    mx = lbf.max(); return mx + math.log(np.exp(lbf - mx).sum()) - math.log(len(lbf))


class InputAxis:
    """Beta-Bernoulli per bin: each bin sees 0 or 1 at each item. g: forgetting factor of the reference (1 = no forgetting);
    M: maximum length of a stretch (no limit when huge)."""
    def __init__(self, L, g=1.0, M=10 ** 12):
        self.L = L; self.nr = np.zeros(L); self.kr = np.zeros(L); self.m = np.zeros(L); self.j = np.zeros(L); self.lbf = np.zeros(L)
        self.g, self.M = g, M

    def step(self, idx, y):
        self.nr[idx] *= self.g; self.kr[idx] *= self.g
        self.m[idx] += 1; self.j[idx] += y
        nr, kr, m, j = self.nr[idx], self.kr[idx], self.m[idx], self.j[idx]
        self.lbf[idx] = (lbeta(j + .5, m - j + .5) - lbeta(.5, .5)) - (lbeta(kr + j + .5, nr - kr + m - j + .5) - lbeta(kr + .5, nr - kr + .5))
        v = idx[(self.lbf[idx] <= 0) | (self.nr[idx] < MIN_REFERENCE) | (self.m[idx] >= self.M)]
        self.nr[v] += self.m[v]; self.kr[v] += self.j[v]; self.m[v] = 0; self.j[v] = 0; self.lbf[v] = 0

    def reset(self, accused=None):
        """Folds every stretch into the reference; the bins in `accused` start a new reference from nothing."""
        if accused is not None:
            self.nr[accused] = 0; self.kr[accused] = 0
        o = np.ones(self.L, bool)
        if accused is not None: o[accused] = False
        self.nr[o] += self.m[o]; self.kr[o] += self.j[o]; self.m[:] = 0; self.j[:] = 0; self.lbf[:] = 0


class RelationAxis:
    """Gamma-Poisson per bin and class: observed count j against expected count E; the rate of the stretch against the reference."""
    def __init__(self, L, g=1.0, M=10 ** 12):
        self.L = L; self.Er = np.zeros(L); self.kr = np.zeros(L); self.E = np.zeros(L); self.j = np.zeros(L); self.lbf = np.zeros(L)
        self.nr = np.zeros(L); self.m = np.zeros(L)
        self.g, self.M = g, M

    @staticmethod
    def _lm(a, b, j, E):
        return a * np.log(b) - _lg(a) + _lg(a + j) - (a + j) * np.log(b + E)

    def step(self, idx, observed, expected):
        self.Er[idx] *= self.g; self.kr[idx] *= self.g; self.nr[idx] *= self.g
        self.E[idx] += expected; self.j[idx] += observed; self.m[idx] += 1
        a, b = .5 + self.kr[idx], .5 + self.Er[idx]
        self.lbf[idx] = self._lm(.5, .5, self.j[idx], self.E[idx]) - self._lm(a, b, self.j[idx], self.E[idx])
        v = idx[(self.lbf[idx] <= 0) | (self.nr[idx] < MIN_REFERENCE) | (self.m[idx] >= self.M)]
        self.Er[v] += self.E[v]; self.kr[v] += self.j[v]; self.nr[v] += self.m[v]; self.E[v] = 0; self.j[v] = 0; self.m[v] = 0; self.lbf[v] = 0

    def reset(self):
        self.Er[:] = 0; self.kr[:] = 0; self.E[:] = 0; self.j[:] = 0; self.lbf[:] = 0; self.nr[:] = 0; self.m[:] = 0


def logistic_regression(B, y, l2=1e-2, tol=1e-12):
    """The reference model: mean logistic loss + l2/2 |w|^2 (intercept included in the penalty), solved by L-BFGS."""
    X = np.hstack([B, np.ones((len(B), 1))]); n = len(y)

    def f(w):
        z = X @ w
        loss = np.logaddexp(0, z) - y * z
        p = 1 / (1 + np.exp(-z))
        return loss.mean() + .5 * l2 * w @ w, X.T @ (p - y) / n + l2 * w

    r = minimize(f, np.zeros(X.shape[1]), jac=True, method="L-BFGS-B", options={"maxiter": 5000, "gtol": tol, "ftol": 1e-15})
    return r.x
