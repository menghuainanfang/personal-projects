param([Parameter(ValueFromRemainingArguments=$true)][string[]]$MinerArgs)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '本地环境.ps1')
& (Join-Path $PSScriptRoot '.venvs/mineru/Scripts/mineru.exe') @MinerArgs
exit $LASTEXITCODE
