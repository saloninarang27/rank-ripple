"""A2: logical workers owner(v,P)=v mod P; count local/remote PageRank messages."""
import argparse

from common import directed_edges, load_ratings, write_csv

HEADER = ["workers", "local_directed_edges", "remote_directed_edges", "remote_fraction",
          "messages_per_iteration", "remote_bytes_per_iteration",
          "remote_bytes_for_10_iterations"]


def partition_row(edges, p, message_bytes, iterations):
    remote = sum(1 for s, d in edges if s % p != d % p)
    total = len(edges)
    per_iter = remote * message_bytes
    return [p, total - remote, remote, remote / total, total, per_iter, per_iter * iterations]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--workers", type=int, nargs="+", default=[4, 8, 16, 32])
    ap.add_argument("--message-bytes", type=int, default=16)
    ap.add_argument("--iterations", type=int, default=10)
    ap.add_argument("--output", default="partA/output/partition_messages.csv")
    a = ap.parse_args()
    if any(p < 1 for p in a.workers):
        raise SystemExit("--workers must be >= 1")
    edges = directed_edges(load_ratings(a.data_dir))
    rows = [partition_row(edges, p, a.message_bytes, a.iterations) for p in a.workers]
    # column name is fixed by the spec; value uses --iterations (default 10)
    write_csv(a.output, HEADER, rows)
    print(",".join(HEADER))
    for r in rows:
        print(",".join(map(str, r)))


if __name__ == "__main__":
    main()
