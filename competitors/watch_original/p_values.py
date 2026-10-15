"""Funções copiadas sem mudança de github.com/aaronhan223/watch, commit 3d17fca58ac60410d020b54dee19ee3fc4ec29c2, src/p_values.py (só esta; o resto do arquivo importa torch e não é usado)."""
import numpy as np


def calculate_p_values(conformity_scores):
    """
    Calculate the conformal p-values from conformity scores.
    """
    
    n = len(conformity_scores)
    p_values = np.array([(np.sum(conformity_scores[:i] > conformity_scores[i]) + 
                         np.random.uniform() * np.sum(conformity_scores[:(i+1)] == conformity_scores[i])) / (i + 1)
                         for i in range(n)])
    return p_values
