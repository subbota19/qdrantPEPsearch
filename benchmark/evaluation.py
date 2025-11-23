from typing import Dict, Iterable, List

import numpy as np


def recall_at_k(
    results: Iterable[Dict[str, str]],
    expected_results: Iterable[str],
    key: str,
    k: int = 10,
):
    top_k = [r.get(key) for r in results[:k]]
    return 1.0 if any(url in top_k for url in expected_results) else 0.0


def mrr(results: Iterable[Dict[str, str]], expected_results: Iterable[str], key: str):
    for idx, r in enumerate(results, start=1):
        if r.get(key) in expected_results:
            return 1.0 / idx
    return 0.0


def p_latency(latencies: List[float], q: int):
    return np.percentile(latencies, q)
