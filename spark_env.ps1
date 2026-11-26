# Windows-only helper: dot-source before spark-submit:   . .\spark_env.ps1
# Spark's .cmd launchers break on paths containing spaces, so 8.3 short paths are used.
# Edit $JdkDir / $HadoopDir if Java 21 / winutils live elsewhere on your machine.
$JdkDir    = (Resolve-Path "$PSScriptRoot\..\tools\jdk-21*").Path
$HadoopDir = "$PSScriptRoot\..\tools\hadoop"

$fso = New-Object -ComObject Scripting.FileSystemObject
$root = $fso.GetFolder($PSScriptRoot).ShortPath
$env:JAVA_HOME   = $fso.GetFolder($JdkDir).ShortPath
if (Test-Path "$HadoopDir\bin\winutils.exe") { $env:HADOOP_HOME = $fso.GetFolder($HadoopDir).ShortPath }
$env:SPARK_HOME  = "$root\.venv\Lib\site-packages\pyspark"
$env:PYSPARK_PYTHON        = "$root\.venv\Scripts\python.exe"
$env:PYSPARK_DRIVER_PYTHON = $env:PYSPARK_PYTHON
$env:PATH = "$env:JAVA_HOME\bin;$root\.venv\Scripts;$env:PATH"
if ($env:HADOOP_HOME) { $env:PATH = "$env:HADOOP_HOME\bin;$env:PATH" }
Write-Host "JAVA_HOME=$env:JAVA_HOME"
Write-Host "HADOOP_HOME=$env:HADOOP_HOME"
Write-Host "SPARK_HOME=$env:SPARK_HOME"
