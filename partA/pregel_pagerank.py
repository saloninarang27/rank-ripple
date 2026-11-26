"""A4: the same 10-iteration PageRank using the GraphFrames Pregel API.

Run (from submission root):
  spark-submit --master "local[*]" --packages io.graphframes:graphframes-spark4_2.13:0.12.3 \
      partA/pregel_pagerank.py --data-dir <ml-100k> --iterations 10 --damping 0.85 \
      --output partA/output/pregel_pagerank.csv

Also writes pagerank_compare.csv (next to --output), comparing against
pagerank_local.pagerank() run with the same iterations/damping.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# graphframes-py 0.12.3 imports typing_extensions (Self, override) but does not declare it
# as a dependency. Python >= 3.12 has both in stdlib typing, so alias it if missing; this
# keeps requirements.txt at exactly the six pinned packages.
try:
    import typing_extensions  # noqa: F401
except ImportError:
    import typing
    sys.modules["typing_extensions"] = typing

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from graphframes import GraphFrame
from graphframes.lib import Pregel

from common import directed_edges, load_ratings, write_csv
from pagerank_local import pagerank, rank_rows


def pregel_pagerank(spark, edges, iterations, damping):
    vertices = sorted({v for e in edges for v in e})
    n = len(vertices)
    e_df = spark.createDataFrame(edges, "src LONG, dst LONG")
    out_deg = e_df.groupBy("src").agg(F.count("*").alias("out_degree"))
    v_df = (spark.createDataFrame([(v,) for v in vertices], "id LONG")
            .join(out_deg.withColumnRenamed("src", "id"), "id", "left")
            .fillna(0, ["out_degree"]))
    g = GraphFrame(v_df, e_df)

    result = (
        g.pregel
        .setMaxIter(iterations)                       # superstep count
        .setCheckpointInterval(2)                     # cut lineage every 2 supersteps
        .setUseLocalCheckpoints(True)                 # executor-local: no checkpoint dir needed
        .withVertexColumn(
            "rank",                                   # vertex state
            F.lit(1.0 / n),                           # PR_0(v) = 1/N
            # vertex update: PR_{t+1} = (1-d)/N + d * sum(msgs)
            F.lit((1 - damping) / n) + F.lit(damping) * F.coalesce(Pregel.msg(), F.lit(0.0)),
        )
        # message generation: PR_t(u)/out_degree(u) along every edge u->v
        .sendMsgToDst(Pregel.src("rank") / Pregel.src("out_degree"))
        .aggMsgs(F.sum(Pregel.msg()))                 # message aggregation
        .run()
    )
    return {int(r["id"]): float(r["rank"]) for r in result.select("id", "rank").collect()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--iterations", type=int, default=10)
    ap.add_argument("--damping", type=float, default=0.85)
    ap.add_argument("--output", default="partA/output/pregel_pagerank.csv")
    ap.add_argument("--shuffle-partitions", type=int, default=8)
    a = ap.parse_args()

    edges = directed_edges(load_ratings(a.data_dir))
    # 200k edges: default 200 shuffle partitions is pure task overhead on one laptop
    spark = (SparkSession.builder.appName("A3A-pregel-pagerank")
             .config("spark.sql.shuffle.partitions", str(a.shuffle_partitions))
             .getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    try:
        pregel = pregel_pagerank(spark, edges, a.iterations, a.damping)
    finally:
        spark.stop()

    write_csv(a.output, ["vertex_id", "vertex_type", "original_id", "pagerank"], rank_rows(pregel))

    local, _ = pagerank(edges, a.iterations, a.damping)
    diffs = [abs(local[v] - pregel[v]) for v in local]
    compare = [a.iterations, repr(max(diffs)), repr(sum(diffs) / len(diffs)),
               repr(sum(local.values())), repr(sum(pregel.values()))]
    write_csv(os.path.join(os.path.dirname(os.path.abspath(a.output)), "pagerank_compare.csv"),
              ["iterations", "max_abs_difference", "mean_abs_difference",
               "local_rank_sum", "pregel_rank_sum"], [compare])
    print("compare:", compare)
    if max(diffs) > 1e-8:
        raise SystemExit("FAIL: max_abs_difference > 1e-8")


if __name__ == "__main__":
    main()
