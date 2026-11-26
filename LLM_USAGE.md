# LLM Usage — Assignment 3A

## Tools used
- **Claude Code** (Anthropic), model Claude Opus 5.5, used inside VS Code as a coding agent. It read the assignment, wrote and ran the scripts, and I reviewed and ran every output myself.

The session was conversational. The prompts below are condensed versions of the turns that changed the implementation, in the order they happened. Each one shows what came back, what was wrong, and how the next prompt refined it.

## Prompts and iterations

### Round 1 — Implement the pure-Python tasks from the specification
> "Read Sections 3–5 and A0–A7 of the assignment. Implement graph_stats.py, partition_messages.py, pagerank_local.py and powergraph_sim.py exactly as specified: user id = user_id, movie id = 100000 + movie_id, owner(v,P) = v mod P, PageRank as explicit message passing with no PageRank library, exactly 10 iterations. Every program must take --data-dir, and no parameter may be hard-coded, because the TA will run with workers=7, iterations=4 and hub-degree=5000."

**Result:** all four scripts ran first time, and the fixed counts matched (2625 / 943 / 1682 / 100000 / 200000 / 1 / 5).
**What I checked:** a matching rank sum alone doesn't prove PageRank is right.

### Round 2 — Independent verification instead of trusting the output
> "Write a self-check that runs with non-default parameters (P=7, 4 iterations, H=5000) and verifies PageRank against an independent method: build the dense column-stochastic matrix in numpy and do power iteration."

**Result:** `test_partA.py`. Message-passing PageRank equals the matrix version within 1e-15. local + remote = 200000 for P=7, and the vertex/edge-partition mean-work formulas hold.

### Round 3 — Pregel with GraphFrames (first version)
> "Implement the same PageRank with the GraphFrames 0.12.3 Pregel API (withVertexColumn / sendMsgToDst / aggMsgs), not graph.pageRank(). Write pagerank_compare.csv against the local implementation with identical iterations and damping."

**Problems on Windows, fixed one at a time by pasting the exact error back:**
1. `Failed to find Spark jars directory`. Spark's `.cmd` launchers break when the path has spaces (`M.Tech CSE\3rd Semester CSE`). Fix: `spark_env.ps1` uses 8.3 short paths for `SPARK_HOME`, `JAVA_HOME` and `PYSPARK_PYTHON`.
2. `ModuleNotFoundError: typing_extensions`. graphframes-py 0.12.3 imports it but doesn't declare it. The LLM noted that `pip install typing_extensions` would break the "exactly six pinned packages" rule. Fix: alias it to the stdlib `typing` module when it's missing (Python 3.14 has `Self` and `override`).
3. `HADOOP_HOME and hadoop.home.dir are unset`. See the wrong suggestion below.

### Round 4 — Spark was extremely slow and then crashed
> "The Pregel job takes about 90 seconds per superstep and then fails with java.lang.OutOfMemoryError: Java heap space inside QueryExecution.explainString. Here is the log. Why does a 2,625-vertex graph run out of memory?"

**Diagnosis:** the first version had `setCheckpointInterval(0)`, so every superstep stacked a new join and aggregate on top of the previous plan. The logical plan grew with each iteration until even printing it exhausted the heap. Spark's default of 200 shuffle partitions added more task overhead.
**Fix:** `setCheckpointInterval(2)` with `setUseLocalCheckpoints(True)` (cuts the lineage, needs no checkpoint directory) and `spark.sql.shuffle.partitions=8`. Runtime dropped from a crash after about 10 minutes to **56 s**, with max |local − Pregel| = **4.3e-18** (limit 1e-8). A 4-iteration run also matched (3.0e-18).

### Round 5 — Presentation and reproducibility
> "The plot's value labels for the edge-partition line are clipped at the bottom. Also give me one command that regenerates every output file and runs the self-check."

**Result:** the labels moved above the points, and `run_all.ps1` reproduces all 9 output files in about 60 s.

## Example where the LLM suggestion was wrong

**1. Disabling checkpointing (main example).** In Round 3 the LLM chose `setCheckpointInterval(0)`, reasoning that "with 2,625 vertices the query plan stays small and no checkpoint directory is needed". That was conceptually wrong. In a DataFrame-based Pregel, every superstep adds to the lineage no matter how small the graph is. The result was 90 s per superstep and then `OutOfMemoryError`.

**2. Trying to avoid winutils.exe.** For the `HADOOP_HOME` error, the LLM first suggested passing the GraphFrames jars with `--jars`, then with `spark.jars` through `PYSPARK_SUBMIT_ARGS`, instead of using `--packages`. Both failed with the same error, because SparkContext itself calls Hadoop's `FileUtil.chmod` on Windows. The real fix was installing `winutils.exe` / `hadoop.dll` into `HADOOP_HOME\bin`.

## How the problems were detected and fixed
- **Detection:** ran the exact command required by the assignment and read the real log instead of accepting "it should work". The OOM stack trace (`explainString` → `generateTreeString` repeated) pointed directly at an oversized query plan.
- **Fix:** checkpointing every 2 supersteps with local checkpoints, plus 8 shuffle partitions. Verified by rerunning with 10 and with 4 iterations and checking `pagerank_compare.csv` each time (both under 1e-17).
- For winutils: confirmed from the stack trace that the failure was in `SparkContext.addFile` → `FileUtil.chmod`, which every launch path goes through. That made it clear the workaround could not succeed.

## Concept that became clearer
**Communication and lineage are costs of the execution model, not of the data size.** With `v mod P`, about 1 − 1/P of PageRank messages are remote (75% → 97% for P = 4 → 32), no matter how good the code is. A DataFrame-based Pregel grows its query plan every superstep unless it checkpoints, even for a tiny graph. Likewise, a hub's cost lands entirely on its owning worker under vertex partitioning (imbalance 2.13 at H = 50,000). A vertex cut spreads those edges evenly (imbalance 1.0) and pays a sync cost of `2 × (replicas − 1)` that doesn't depend on the hub's degree.
