param([Parameter(ValueFromRemainingArguments=$true)][string[]]$PdfArgs)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '本地环境.ps1')
if (-not $PdfArgs) { $PdfArgs = @('--gui','--lang-in','en','--lang-out','zh','--ui-lang','zh','--disable-config-auto-save') }
& (Join-Path $PSScriptRoot 'tools/pdf2zh/pdf2zh/pdf2zh.exe') @PdfArgs
exit $LASTEXITCODE
