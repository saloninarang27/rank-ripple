"""Shared helpers for Assignment 3A: reading u.data and the vertex-ID mapping."""
import csv
import os

MOVIE_OFFSET = 100000


def movie_vid(movie_id):
    return MOVIE_OFFSET + movie_id


def vertex_info(vid):
    """Return (vertex_type, original_id) for an execution-graph vertex id."""
    if vid > MOVIE_OFFSET:
        return "movie", vid - MOVIE_OFFSET
    return "user", vid


def load_ratings(data_dir):
    """Read u.data -> list of (user_id, movie_id, rating, timestamp) ints."""
    path = os.path.join(data_dir, "u.data")
    if not os.path.isfile(path):
        raise SystemExit(f"u.data not found in --data-dir {data_dir!r}")
    rows = []
    with open(path, encoding="ascii") as f:
        for line in f:
            u, m, r, t = map(int, line.split("\t"))
            rows.append((u, m, r, t))
    return rows


def directed_edges(ratings):
    """Execution graph G_D: each rating {u,m} becomes u->m and m->u."""
    edges = []
    for u, m, _, _ in ratings:
        mv = movie_vid(m)
        edges.append((u, mv))
        edges.append((mv, u))
    return edges


def ensure_parent(path):
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)


def write_csv(path, header, rows):
    ensure_parent(path)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
