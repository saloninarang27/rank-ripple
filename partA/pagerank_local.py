"""A3: PageRank as explicit message passing (no PageRank library)."""
import argparse
import os
from collections import Counter

from common import directed_edges, load_ratings, vertex_info, write_csv


def pagerank(edges, iterations, damping):
    """Return (final_ranks dict, trace list of (iteration, rank_sum, l1_change))."""
    vertices = sorted({v for e in edges for v in e})
    n = len(vertices)
    out_deg = Counter(s for s, _ in edges)
    pr = {v: 1.0 / n for v in vertices}
    trace = [(0, sum(pr.values()), 0.0)]
    for t in range(iterations):
        inbox = dict.fromkeys(vertices, 0.0)
        for s, d in edges:                      # one message per directed edge
            inbox[d] += pr[s] / out_deg[s]
        new = {v: (1 - damping) / n + damping * inbox[v] for v in vertices}
        l1 = sum(abs(new[v] - pr[v]) for v in vertices)
        pr = new
        trace.append((t + 1, sum(pr.values()), l1))
    return pr, trace


def rank_rows(pr):
    order = sorted(pr, key=lambda v: (-pr[v], v))
    return [[v, *vertex_info(v), repr(pr[v])] for v in order]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--iterations", type=int, default=10)
    ap.add_argument("--damping", type=float, default=0.85)
    ap.add_argument("--output-dir", default="partA/output")
    a = ap.parse_args()
    pr, trace = pagerank(directed_edges(load_ratings(a.data_dir)), a.iterations, a.damping)
    write_csv(os.path.join(a.output_dir, "pagerank_local.csv"),
              ["vertex_id", "vertex_type", "original_id", "pagerank"], rank_rows(pr))
    write_csv(os.path.join(a.output_dir, "pagerank_trace.csv"),
              ["iteration", "rank_sum", "l1_change"], [[i, repr(s), repr(l)] for i, s, l in trace])
    for i, s, l in trace:
        print(f"iter {i:2d}  rank_sum={s:.15f}  l1_change={l:.3e}")
    print("top 5:", rank_rows(pr)[:5])


if __name__ == "__main__":
    main()
