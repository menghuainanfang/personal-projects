param([Parameter(ValueFromRemainingArguments=$true)][string[]]$WorkflowArgs)
$ErrorActionPreference = 'Stop'
$cfg = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'config.json') -Raw | ConvertFrom-Json
& $cfg.python (Join-Path $PSScriptRoot 'scripts/workflow.py') @WorkflowArgs
exit $LASTEXITCODE
