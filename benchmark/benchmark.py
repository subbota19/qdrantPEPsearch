from pathlib import Path

from benchmark.evaluation import recall_at_k, mrr, p_latency
from benchmark.timer import CodeTimer
from benchmark.utils import load_tests, load_configs
from search.search import PEPSearchEngine

CONFIG_PATH = f'{Path(__file__).resolve().parent}/config/config.yaml'


def benchmark_evaluation():
    tests = load_tests(path=CONFIG_PATH)
    configs = load_configs(path=CONFIG_PATH)

    pep_search_engine = PEPSearchEngine()

    for cfg in configs:
        cfg_name = cfg.get('name')
        dense_limit = cfg.get('dense_limit')
        sparse_limit = cfg.get('sparse_limit')
        rff_limit = cfg.get('rff_limit')

        print(f'\n=== Running config: {cfg_name} ===')

        metrics = {
            'recall': [],
            'mrr': [],
            'latency': [],
        }

        test_count = len(tests)

        for test in tests:
            query = test.get('query')
            expected = test.get('expected')

            with CodeTimer() as ct:
                results = pep_search_engine.search(
                    query=query,
                    dense_limit=dense_limit,
                    sparse_limit=sparse_limit,
                    rff_limit=rff_limit,
                )

            metrics['latency'].append(ct.elapsed)

            rec = recall_at_k(results, expected_results=expected, key='section_url')
            mrr_score = mrr(results, expected_results=expected, key='section_url')

            metrics['recall'].append(rec)
            metrics['mrr'].append(mrr_score)

        avg_recall = sum(metrics['recall']) / test_count
        avg_mrr = sum(metrics['mrr']) / test_count
        p50 = p_latency(metrics['latency'], 50)
        p95 = p_latency(metrics['latency'], 95)

        summary = {
            'recall@10': avg_recall,
            'mrr@10': avg_mrr,
            'latency_p50': p50,
            'latency_p95': p95,
        }

        print(f'Results for {cfg_name}:')
        for metric, value in summary.items():
            print(f'\t{metric}: {value}')


benchmark_evaluation()
