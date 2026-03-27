$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = "python"
$logDir = Join-Path $projectRoot "log/server"
$stdoutLog = Join-Path $logDir "api_server_8013.log"
$stderrLog = Join-Path $logDir "api_server_8013.err.log"

if (!(Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

Start-Process `
    -FilePath $pythonExe `
    -ArgumentList "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8013" `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog

Write-Output "API started: http://0.0.0.0:8013"
Write-Output "stdout: $stdoutLog"
Write-Output "stderr: $stderrLog"
