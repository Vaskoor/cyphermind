"""
Bradley-Terry Preference Model
================================
Given pairwise comparisons (A beats B), fit scores s_i such that:
  P(i beats j) = s_i / (s_i + s_j)

Fit via MLE with scipy.optimize.minimize (L-BFGS-B).

Pseudocode:
  1. Collect preference pairs from DB
  2. Encode unique items (agent combos / report styles)
  3. Build log-likelihood function
  4. Minimize negative log-likelihood
  5. Return scores dict

Complexity: O(n_pairs × n_items) per optimization call
"""
from __future__ import annotations
import logging
import numpy as np
from scipy.optimize import minimize
from typing import Optional

logger = logging.getLogger(__name__)

def fit_bradley_terry(
    pairs: list[tuple[str, str, str]]  # (item_a, item_b, winner: "a"|"b")
) -> dict[str, float]:
    """
    Fit Bradley-Terry model.

    Parameters
    ----------
    pairs : list of (item_a, item_b, winner)

    Returns
    -------
    dict mapping item → score (higher = better)
    """
    if not pairs:
        return {}

    # Collect unique items
    items = sorted({item for a, b, _ in pairs for item in (a, b)})
    item_idx = {item: i for i, item in enumerate(items)}
    n = len(items)

    # Build win matrix W[i][j] = times i beat j
    W = np.zeros((n, n))
    for a, b, winner in pairs:
        i, j = item_idx[a], item_idx[b]
        if winner == "a":
            W[i][j] += 1
        else:
            W[j][i] += 1

    def neg_log_likelihood(log_scores: np.ndarray) -> float:
        """Negative log-likelihood of Bradley-Terry model."""
        s = np.exp(log_scores)
        ll = 0.0
        for i in range(n):
            for j in range(n):
                if W[i][j] > 0:
                    ll += W[i][j] * (log_scores[i] - np.log(s[i] + s[j] + 1e-10))
        return -ll

    x0 = np.zeros(n)
    result = minimize(neg_log_likelihood, x0, method="L-BFGS-B")

    if not result.success:
        logger.warning(f"Bradley-Terry optimization did not converge: {result.message}")

    scores = dict(zip(items, np.exp(result.x).tolist()))
    # Normalize to [0, 1]
    max_score = max(scores.values()) or 1
    return {k: v / max_score for k, v in scores.items()}
