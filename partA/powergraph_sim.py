"""A5/A6: deterministic simulation of Pregel vertex partition vs PowerGraph vertex cut.

Writes for the given --workers/--hub-degree:  powergraph_results.csv
and for --workers with every --scaling-hubs:   powergraph_scaling.csv + powergraph_scaling.png
"""
import argparse
import os
from collections import Counter, defaultdict

from common import load_ratings, movie_vid, write_csv

HUB = 200000
SYNTH_BASE = 300000

RESULT_HEADER = ["workers", "hub_degree", "vertex_partition_max_work",
                 "vertex_partition_mean_work", "vertex_partition_imbalance", "hub_owner",
                 "hub_owner_work", "edge_partition_max_work", "edge_partition_mean_work",
                 "edge_partition_imbalance", "replication_factor", "hub_replica_count",
                 "gas_sync_messages"]
SCALING_HEADER = ["hub_degree", "vertex_partition_imbalance", "edge_partition_imbalance",
                  "replication_factor", "gas_sync_messages"]


def hub_graph(ratings, h):
    """Undirected HUB-GRAPH edges as (min_endpoint, max_endpoint)."""
    edges = [(u, movie_vid(m)) for u, m, _, _ in ratings]
    edges += [(HUB, SYNTH_BASE + i) for i in range(1, h + 1)]
    return [(min(a, b), max(a, b)) for a, b in edges]


def simulate(edges, p, h):
    deg = Counter()
    for a, b in edges:
        deg[a] += 1
        deg[b] += 1
    assert deg[HUB] == h

    # Pregel-style vertex partition: work = sum of degrees of owned vertices
    vwork = [0] * p
    for v, d in deg.items():
        vwork[v % p] += d
    assert sum(vwork) == 2 * len(edges)
    v_mean = sum(vwork) / p

    # PowerGraph-style edge partition: sorted edge_id mod P
    ework = [0] * p
    replicas = defaultdict(set)
    for eid, (a, b) in enumerate(sorted(edges)):
        w = eid % p
        ework[w] += 1
        replicas[a].add(w)
        replicas[b].add(w)
    e_mean = sum(ework) / p
    total_replicas = sum(len(s) for s in replicas.values())
    # "original vertices" = every vertex of HUB-GRAPH (each counted once, before replication)
    n_vertices = len(deg)

    return {
        "workers": p,
        "hub_degree": h,
        "vertex_partition_max_work": max(vwork),
        "vertex_partition_mean_work": v_mean,
        "vertex_partition_imbalance": max(vwork) / v_mean,
        "hub_owner": HUB % p,
        "hub_owner_work": vwork[HUB % p],
        "edge_partition_max_work": max(ework),
        "edge_partition_mean_work": e_mean,
        "edge_partition_imbalance": max(ework) / e_mean,
        "replication_factor": total_replicas / n_vertices,
        "hub_replica_count": len(replicas[HUB]),
        "gas_sync_messages": 2 * (total_replicas - n_vertices),
    }


def plot(rows, p, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    xs = [r["hub_degree"] for r in rows]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(xs, [r["vertex_partition_imbalance"] for r in rows], "o-",
            label="Vertex partition (Pregel, v mod P)")
    ax.plot(xs, [r["edge_partition_imbalance"] for r in rows], "s-",
            label="Edge partition / vertex cut (PowerGraph)")
    for r in rows:
        ax.annotate(f'{r["vertex_partition_imbalance"]:.3f}',
                    (r["hub_degree"], r["vertex_partition_imbalance"]),
                    textcoords="offset points", xytext=(0, 6), ha="center", fontsize=8)
        ax.annotate(f'{r["edge_partition_imbalance"]:.3f}',
                    (r["hub_degree"], r["edge_partition_imbalance"]),
                    textcoords="offset points", xytext=(0, 6), ha="center", fontsize=8)
    ax.set_xlabel("Hub degree H (linear scale)")
    ax.set_ylabel("Load imbalance = max(work) / mean(work)")
    ax.set_title(f"Hub scaling, P = {p} workers")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--hub-degree", type=int, default=50000)
    ap.add_argument("--scaling-hubs", type=int, nargs="+", default=[1000, 10000, 50000])
    ap.add_argument("--output-dir", default="partA/output")
    a = ap.parse_args()
    if a.workers < 1 or a.hub_degree < 1 or min(a.scaling_hubs) < 1:
        raise SystemExit("--workers and hub degrees must be >= 1")
    ratings = load_ratings(a.data_dir)
    os.makedirs(a.output_dir, exist_ok=True)

    res = simulate(hub_graph(ratings, a.hub_degree), a.workers, a.hub_degree)
    write_csv(os.path.join(a.output_dir, "powergraph_results.csv"), RESULT_HEADER,
              [[res[k] for k in RESULT_HEADER]])
    for k in RESULT_HEADER:
        print(f"{k}: {res[k]}")

    rows = [simulate(hub_graph(ratings, h), a.workers, h) for h in sorted(a.scaling_hubs)]
    write_csv(os.path.join(a.output_dir, "powergraph_scaling.csv"), SCALING_HEADER,
              [[r[k] for k in SCALING_HEADER] for r in rows])
    plot(rows, a.workers, os.path.join(a.output_dir, "powergraph_scaling.png"))
    print("scaling:")
    for r in rows:
        print("  ", [r[k] for k in SCALING_HEADER])


if __name__ == "__main__":
    main()
