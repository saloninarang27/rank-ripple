# Assignment 3A — Graph Processing, PageRank, Pregel and PowerGraph

## 1. Student

- Name: Saloni
- Roll number: MT25081

## 2. Hardware

| Item | Value |
|---|---|
| OS | Microsoft Windows 11 Home Single Language (10.0.26300) |
| CPU | 11th Gen Intel(R) Core(TM) i5-1155G7 @ 2.50GHz |
| Logical CPUs | 8 |
| RAM | 15.8 GB |

## 3. Software versions

Full output of `python --version`, `java -version` and `pip show` is in [environment.txt](environment.txt).

```
Python 3.14.2
openjdk version "21.0.13" 2026-10-20 LTS (Temurin-21.0.13+9)
graphframes-py==0.12.3
matplotlib==3.11.2
neo4j==6.4.1
networkx==3.7
pandas==3.1.0
pyspark==4.2.0
```

GraphFrames JVM package: `io.graphframes:graphframes-spark4_2.13:0.12.3` (passed with `--packages`).

## 4. Dataset

- MovieLens 100K from https://files.grouplens.org/datasets/movielens/ml-100k.zip
- Archive MD5 checked: `0e33842e24a9c977be4e0107933c0723` (matches the expected value)
- Row-count check: `u.data` has 100,000 rows, users 1..943, movies 1..1682, ratings 1..5 (see `graph_stats.csv`)
- Path assumption: the archive is extracted **outside** the submission, e.g. `../data/ml-100k`. All programs take `--data-dir`. No paths are hard-coded and the dataset is not included in the submission.

## 5. How to run

### 5.1 One-time setup (Windows PowerShell)

```powershell
py -3.14 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# dataset (outside the submission folder)
mkdir ..\data; cd ..\data
curl.exe -LO https://files.grouplens.org/datasets/movielens/ml-100k.zip
Get-FileHash -Algorithm MD5 ml-100k.zip      # expect 0E33842E24A9C977BE4E0107933C0723
Expand-Archive ml-100k.zip -DestinationPath .
cd ..\3A
```

On Linux/macOS use `python3.14 -m venv .venv; source .venv/bin/activate`. The commands in 5.2 are the same.

**Quickest way (Windows):** in a PowerShell terminal (the VS Code terminal works too) in this folder, run `.\run_all.ps1`. It runs every command below in order, then the self-check, in about 1 minute. Use `.\run_all.ps1 -DataDir <path>` if the dataset is somewhere else.

### 5.2 Commands used to produce every file in `partA/output/`

Run from the submission root with the venv active. Here `<D>` = `../data/ml-100k`.

```bash
python partA/graph_stats.py --data-dir <D> --output partA/output/graph_stats.csv
python partA/partition_messages.py --data-dir <D> --workers 4 8 16 32 --message-bytes 16 --iterations 10 --output partA/output/partition_messages.csv
python partA/pagerank_local.py --data-dir <D> --iterations 10 --damping 0.85 --output-dir partA/output
spark-submit --master "local[*]" --packages io.graphframes:graphframes-spark4_2.13:0.12.3 partA/pregel_pagerank.py --data-dir <D> --iterations 10 --damping 0.85 --output partA/output/pregel_pagerank.csv
python partA/powergraph_sim.py --data-dir <D> --workers 8 --hub-degree 50000 --output-dir partA/output
```

| Command | Output files |
|---|---|
| `graph_stats.py` | `graph_stats.csv` |
| `partition_messages.py` | `partition_messages.csv` |
| `pagerank_local.py` | `pagerank_local.csv`, `pagerank_trace.csv` |
| `pregel_pagerank.py` | `pregel_pagerank.csv`, `pagerank_compare.csv` (written next to `--output`; uses the same `--iterations`/`--damping`) |
| `powergraph_sim.py` | `powergraph_results.csv` (for `--workers`/`--hub-degree`), `powergraph_scaling.csv` and `powergraph_scaling.png` (for `--workers` with H in `--scaling-hubs`, default `1000 10000 50000`) |

**Spark on Windows.** Run `. .\spark_env.ps1` before `spark-submit`. It sets `JAVA_HOME` (Java 21), `SPARK_HOME` and `PYSPARK_PYTHON` to the venv, using 8.3 short paths because Spark's `.cmd` launchers break when the folder path contains spaces. Native Windows Spark also needs Hadoop's `winutils.exe` + `hadoop.dll` in `%HADOOP_HOME%\bin`. Without them, `--packages` fails with `HADOOP_HOME and hadoop.home.dir are unset`. Linux, macOS and WSL don't need any of this.

**Self-check with non-default parameters** (P=7, 4 iterations, H=5000, plus an independent numpy matrix PageRank):

```bash
python partA/test_partA.py --data-dir <D>
```

**Parameter changes the TA can try** (none of these values are hard-coded):

```bash
python partA/partition_messages.py --data-dir <D> --workers 7 --output /tmp/pm.csv
python partA/pagerank_local.py --data-dir <D> --iterations 4 --output-dir /tmp/pr
spark-submit ... partA/pregel_pagerank.py --data-dir <D> --iterations 4 --output /tmp/pr/pregel_pagerank.csv
python partA/powergraph_sim.py --data-dir <D> --workers 7 --hub-degree 5000 --output-dir /tmp/pg
```

## 6. Results and answers

### A1 — Graph

`logical_vertices=2625, users=943, movies=1682, logical_edges=100000, directed_edges=200000, ratings 1..5`.
Highest-degree user: **405 (degree 737)**. Highest-degree movie: **50 (Star Wars, degree 583)**. Ties would go to the smallest ID.

### A2 — Message cost

| P | local | remote | remote_fraction | remote bytes / iter |
|---|---|---|---|---|
| 4 | 49,730 | 150,270 | 0.751 | 2,404,320 |
| 8 | 24,832 | 175,168 | 0.876 | 2,802,688 |
| 16 | 12,424 | 187,576 | 0.938 | 3,001,216 |
| 32 | 6,248 | 193,752 | 0.969 | 3,100,032 |

With `v mod P` partitioning, the remote fraction is about 1 − 1/P.

**Why communication matters even on one laptop (≤120 words):**
The program is written against logical workers, and the same code would run unchanged on a cluster. There, every remote message must be serialized, sent over the network, buffered and deserialized before the next superstep can begin. Network bandwidth and latency are orders of magnitude worse than memory access, so the 2.4–3.1 MB of remote traffic per iteration, repeated every iteration, decides how fast the job runs. Hash partitioning makes 75–97% of messages remote, and that share grows with P. Measuring it on a laptop shows the cost before a cluster is used. Even locally, Spark's `local[*]` shuffles these messages between tasks through serialization and shuffle files.

### A3 — Local PageRank

`rank_sum` is 1.0 at every iteration (error < 1e-15), and the L1 change shrinks from 0.91 to 0.11 over 10 iterations. The top vertices are users 405, 655, 181, 13 and then movie 50, which are the highest-degree vertices. This is expected: on an undirected bipartite graph, PageRank is closely tied to degree.

### A4 — Pregel PageRank

`pagerank_compare.csv`: max_abs_difference = **4.34e-18** and mean_abs_difference = 9.6e-20 (the limit is 1e-8). Both rank sums are 1.0. The Pregel run takes about 56 s on `local[*]`.

**Mapping to [pregel_pagerank.py](partA/pregel_pagerank.py) (≤180 words):**

- **Vertex state:** `.withVertexColumn("rank", F.lit(1.0 / n), ...)` (lines 50–52) adds a `rank` column to each vertex, initialised to 1/N. `out_degree` is a fixed vertex attribute joined in beforehand.
- **Message generation:** `.sendMsgToDst(Pregel.src("rank") / Pregel.src("out_degree"))` (line 57). For each edge triplet u→v, it sends PR_t(u)/out_degree(u) to v.
- **Message aggregation:** `.aggMsgs(F.sum(Pregel.msg()))` (line 58) adds up all messages arriving at the same destination ID (a groupBy on dst).
- **Vertex update:** the third argument of `withVertexColumn` (line 54), `(1-d)/N + d * coalesce(msg, 0)`, replaces `rank` after aggregation.
- **Superstep:** one Pregel iteration is generate → aggregate → update. `.setMaxIter(iterations)` (line 47) runs exactly 10 of them, with no early stopping. `setCheckpointInterval(2)` with `setUseLocalCheckpoints(True)` cuts the growing query plan every 2 supersteps without needing a checkpoint directory.

### A5 — PowerGraph vertex cut (P=8, H=50000)

| | Vertex partition (Pregel) | Edge partition (PowerGraph) |
|---|---|---|
| max work | 79,837 (worker 0, which owns hub 200000) | 18,750 |
| mean work | 37,500 | 18,750 |
| imbalance | **2.129** | **1.000** |

Other results: hub replicas = 8 (one on every worker), replication factor = 1.292, GAS sync messages = 30,738.

**Why the vertex cut helps despite replicas (≤150 words):**
In a vertex partition, one worker owns the hub and must process all 50,000 of its adjacencies itself. Every superstep then waits for that worker: its load is 2.13× the mean. A vertex cut splits the hub's edges evenly across all 8 workers. Each worker gathers a partial sum over its share of the edges, and only the small partial results are combined at the master. This brings imbalance down to 1.0. The cost is that the hub is copied to all 8 workers, and other vertices are replicated too (1.29 replicas per vertex). Each GAS iteration then needs 2 × (replicas − 1) synchronization messages, 30,738 in total. That number depends on the replica count, not on the hub's degree. For a hub, about 7 small mirror messages per iteration are far cheaper than leaving 7 workers idle while one handles 50k edges.

### A6 — Scaling (P=8)

| H | vertex imbalance | edge imbalance | replication factor | GAS sync msgs |
|---|---|---|---|---|
| 1,000 | 1.098 | 1.000 | 5.239 | 30,738 |
| 10,000 | 1.267 | 1.000 | 2.217 | 30,738 |
| 50,000 | 2.129 | 1.000 | 1.292 | 30,738 |

The vertex-partition imbalance grows linearly with H. The edge-partition imbalance stays at 1.0, because edges are dealt round-robin. The sync-message count does not change: the hub always has 8 replicas and each synthetic user has exactly 1. The replication factor falls only because more and more degree-1 vertices are added to the denominator.

Plot: [powergraph_scaling.png](partA/output/powergraph_scaling.png). The x-axis is linear, and the plotted values are the CSV values.

## 7. Known limitations / deviations

1. **Python 3.14.2 instead of 3.14.10.** This is the 3.14 build installed on this machine; the major and minor version match.
2. **`typing_extensions` shim.** `graphframes-py==0.12.3` imports `typing_extensions` without declaring it as a dependency. `pregel_pagerank.py` aliases it to the stdlib `typing` module (Python ≥3.12 has `Self` and `override`) only when it isn't installed. This keeps `requirements.txt` at exactly the six pinned lines.
3. **Windows Spark launcher needs short paths and winutils.** See section 5.2. This doesn't change any algorithm or output.
4. **`replication_factor` denominator.** "number_of_original_vertices" is read as all vertices of HUB-GRAPH, each counted once before replication: 2625 + 1 + H.
5. **Ties for max degree** (A1) are broken by the smallest ID. There are no ties in this data.
6. **`pagerank_trace.csv`:** `l1_change` is 0 for iteration 0, the initial vector.
7. **`remote_bytes_for_10_iterations`** uses the `--iterations` value (default 10). The column name is fixed by the spec.
8. **Windows Spark shutdown message.** `IOException: Failed to delete ... spark-*\userFiles-*.jar` appears when Spark exits on Windows, because the JVM still has the jar open. It happens after the outputs are written and does not affect results (exit code 0).
