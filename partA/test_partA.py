"""Self-check for Assignment 3A with non-default parameters (what the TA does).

python partA/test_partA.py --data-dir <PATH_TO_ml-100k>
"""
import argparse

import numpy as np

from common import directed_edges, load_ratings
from graph_stats import compute_stats
from pagerank_local import pagerank
from partition_messages import partition_row
from powergraph_sim import HUB, hub_graph, simulate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    a = ap.parse_args()
    ratings = load_ratings(a.data_dir)
    edges = directed_edges(ratings)

    # A1 fixed invariants
    stats = dict(compute_stats(ratings)[0])
    assert [stats[k] for k in ["logical_vertices", "logical_user_vertices",
            "logical_movie_vertices", "logical_edges", "directed_edges",
            "min_rating", "max_rating"]] == [2625, 943, 1682, 100000, 200000, 1, 5]

    # A2 with P=7
    w, local, remote, frac, msgs, b1, b10 = partition_row(edges, 7, 16, 10)
    assert local + remote == msgs == 200000 and b1 == remote * 16 and b10 == b1 * 10
    assert remote == sum(1 for s, d in edges if s % 7 != d % 7)

    # A3 vs independent dense-matrix power iteration, 4 iterations
    pr, trace = pagerank(edges, 4, 0.85)
    assert len(trace) == 5 and all(abs(s - 1) <= 1e-9 for _, s, _ in trace)
    ids = sorted(pr)
    idx = {v: i for i, v in enumerate(ids)}
    n = len(ids)
    out = np.zeros(n)
    for s, _ in edges:
        out[idx[s]] += 1
    M = np.zeros((n, n))
    for s, d in edges:
        M[idx[d], idx[s]] += 1 / out[idx[s]]
    x = np.full(n, 1 / n)
    for _ in range(4):
        x = 0.15 / n + 0.85 * M @ x
    assert max(abs(x[idx[v]] - pr[v]) for v in ids) < 1e-15

    # A5 with P=7, H=5000
    r = simulate(hub_graph(ratings, 5000), 7, 5000)
    assert r["hub_owner"] == HUB % 7 and r["hub_replica_count"] == 7
    assert r["vertex_partition_mean_work"] == 2 * (100000 + 5000) / 7
    assert r["edge_partition_mean_work"] == (100000 + 5000) / 7
    assert r["hub_owner_work"] >= 5000

    print("all 3A self-checks passed")


if __name__ == "__main__":
    main()
