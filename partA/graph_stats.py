"""A1: build G_L and G_D from u.data and write graph_stats.csv."""
import argparse
from collections import Counter

from common import directed_edges, load_ratings, movie_vid, write_csv


def compute_stats(ratings):
    user_deg = Counter(u for u, _, _, _ in ratings)
    movie_deg = Counter(m for _, m, _, _ in ratings)
    logical_edges = {(u, movie_vid(m)) for u, m, _, _ in ratings}
    vertices = set(user_deg) | {movie_vid(m) for m in movie_deg}
    # ties broken by smallest id
    max_user_id = min(user_deg, key=lambda u: (-user_deg[u], u))
    max_movie_id = min(movie_deg, key=lambda m: (-movie_deg[m], m))
    ratings_only = [r for _, _, r, _ in ratings]
    return [
        ("logical_vertices", len(vertices)),
        ("logical_user_vertices", len(user_deg)),
        ("logical_movie_vertices", len(movie_deg)),
        # one logical edge per rating row (u.data has no duplicate pairs)
        ("logical_edges", len(ratings)),
        ("directed_edges", len(directed_edges(ratings))),
        ("min_rating", min(ratings_only)),
        ("max_rating", max(ratings_only)),
        ("max_user_degree", user_deg[max_user_id]),
        ("max_user_id", max_user_id),
        ("max_movie_degree", movie_deg[max_movie_id]),
        ("max_movie_id", max_movie_id),
    ], len(logical_edges)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--output", default="partA/output/graph_stats.csv")
    a = ap.parse_args()
    stats, distinct_pairs = compute_stats(load_ratings(a.data_dir))
    if distinct_pairs != dict(stats)["logical_edges"]:
        print(f"WARNING: {distinct_pairs} distinct (user,movie) pairs")
    write_csv(a.output, ["metric", "value"], stats)
    for k, v in stats:
        print(f"{k},{v}")


if __name__ == "__main__":
    main()
