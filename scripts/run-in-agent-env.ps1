param(
    [string]$TaskName = "default",
    [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
    [string[]]$Command
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$safeTaskName = ($TaskName -replace '[^A-Za-z0-9._-]', "-").Trim("-")
if ([string]::IsNullOrWhiteSpace($safeTaskName)) {
    $safeTaskName = "default"
}

$taskRoot = Join-Path $repoRoot ".tmp/codex/$safeTaskName"
$tempRoot = Join-Path $taskRoot "tmp"
$uvCacheRoot = Join-Path $taskRoot "uv-cache"
$pytestBaseTemp = Join-Path $taskRoot "pytest"
$pytestCacheDir = Join-Path $taskRoot "pytest-cache"

foreach ($path in @($taskRoot, $tempRoot, $uvCacheRoot, $pytestBaseTemp, $pytestCacheDir)) {
    New-Item -ItemType Directory -Path $path -Force | Out-Null
}

$previousTemp = $env:TEMP
$previousTmp = $env:TMP
$previousTmpDir = $env:TMPDIR
$previousUvCache = $env:UV_CACHE_DIR
$previousPytestAddopts = $env:PYTEST_ADDOPTS

try {
    $env:TEMP = $tempRoot
    $env:TMP = $tempRoot
    $env:TMPDIR = $tempRoot
    $env:UV_CACHE_DIR = $uvCacheRoot

    $pytestAddopts = "--basetemp=`"$pytestBaseTemp`" -o cache_dir=`"$pytestCacheDir`""
    if ([string]::IsNullOrWhiteSpace($env:PYTEST_ADDOPTS)) {
        $env:PYTEST_ADDOPTS = $pytestAddopts
    }
    else {
        $env:PYTEST_ADDOPTS = "$pytestAddopts $($env:PYTEST_ADDOPTS)"
    }

    if ($Command.Length -eq 1) {
        & $Command[0]
    }
    else {
        & $Command[0] $Command[1..($Command.Length - 1)]
    }
    exit $LASTEXITCODE
}
finally {
    $env:TEMP = $previousTemp
    $env:TMP = $previousTmp
    $env:TMPDIR = $previousTmpDir
    $env:UV_CACHE_DIR = $previousUvCache
    $env:PYTEST_ADDOPTS = $previousPytestAddopts
}
