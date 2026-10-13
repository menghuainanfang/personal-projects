param([Parameter(ValueFromRemainingArguments=$true)][string[]]$PdfArgs)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '本地环境.ps1')
if (-not $PdfArgs) {
    & (Join-Path $PSScriptRoot '本地模型.ps1') start
    $PdfArgs = @('--gui','--lang-in','en','--lang-out','zh','--ui-lang','zh','--disable-config-auto-save', '--ollama', '--ollama-host', 'http://127.0.0.1:11435', '--ollama-model', 'qwen3:4b-instruct', '--no-auto-extract-glossary', '--disable-rich-text-translate')
}
& (Join-Path $PSScriptRoot 'tools/pdf2zh/pdf2zh/pdf2zh.exe') @PdfArgs
exit $LASTEXITCODE
