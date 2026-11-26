# Windows: regenerate every file in partA/output with the required commands.
# Usage (from this folder):  .\run_all.ps1            or  .\run_all.ps1 -DataDir D:\ml-100k
param([string]$DataDir = "..\data\ml-100k")
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
. .\spark_env.ps1
$py = $env:PYSPARK_PYTHON

function Run($exe, [string[]]$cmdArgs) {
    Write-Host "`n>>> $exe $cmdArgs" -ForegroundColor Cyan
    & $exe @cmdArgs
    if ($LASTEXITCODE -ne 0) { throw "failed: $exe $cmdArgs" }
}

Run $py @("partA/graph_stats.py", "--data-dir", $DataDir, "--output", "partA/output/graph_stats.csv")
Run $py @("partA/partition_messages.py", "--data-dir", $DataDir, "--workers", "4", "8", "16", "32", "--message-bytes", "16", "--iterations", "10", "--output", "partA/output/partition_messages.csv")
Run $py @("partA/pagerank_local.py", "--data-dir", $DataDir, "--iterations", "10", "--damping", "0.85", "--output-dir", "partA/output")
$ErrorActionPreference = "Continue"   # Spark writes harmless WARN lines to stderr
Run "spark-submit" @("--master", "local[*]", "--packages", "io.graphframes:graphframes-spark4_2.13:0.12.3", "partA/pregel_pagerank.py", "--data-dir", $DataDir, "--iterations", "10", "--damping", "0.85", "--output", "partA/output/pregel_pagerank.csv")
$ErrorActionPreference = "Stop"
Run $py @("partA/powergraph_sim.py", "--data-dir", $DataDir, "--workers", "8", "--hub-degree", "50000", "--output-dir", "partA/output")
Run $py @("partA/test_partA.py", "--data-dir", $DataDir)
Write-Host "`nDONE - all outputs in partA/output" -ForegroundColor Green
