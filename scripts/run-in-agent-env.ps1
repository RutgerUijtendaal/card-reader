param(
    [string]$TaskName = "default"
)

$ErrorActionPreference = "Stop"
if ($args.Count -eq 0) {
    throw "A command is required."
}

$runner = Join-Path $PSScriptRoot "run-in-agent-env.py"
& uv run --no-project python $runner --task-name $TaskName -- @args
exit $LASTEXITCODE
