param(
    [Parameter(Mandatory = $true)][string]$Pdf,
    [string]$Output = '',
    [string]$Pages = ''
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '本地环境.ps1')
$sourcePdf = (Resolve-Path -LiteralPath $Pdf).Path
if (-not $Output) { $Output = Join-Path $PSScriptRoot 'output/local-pdf' }
New-Item -ItemType Directory -Path $Output -Force | Out-Null
& (Join-Path $PSScriptRoot '本地模型.ps1') start
$translateStarted = Get-Date
$translateArgs = @(
    $sourcePdf, '--ollama', '--ollama-host', 'http://127.0.0.1:11435',
    '--ollama-model', 'qwen3:4b-instruct', '--lang-in', 'en', '--lang-out', 'zh',
    '--qps', '1', '--pool-max-workers', '1', '--no-auto-extract-glossary',
    '--translate-table-text', '--disable-rich-text-translate',
    '--max-pages-per-part', '50',
    '--output', $Output, '--watermark-output-mode', 'no_watermark'
)
if ($Pages) { $translateArgs += @('--pages', $Pages, '--only-include-translated-page') }
& (Join-Path $PSScriptRoot 'tools/pdf2zh/pdf2zh/pdf2zh.exe') @translateArgs
if ($LASTEXITCODE -ne 0) { throw 'PDF 翻译未完成，请查看运行日志。' }
$outputStem = [System.IO.Path]::GetFileNameWithoutExtension($sourcePdf)
foreach ($kind in @('mono', 'dual')) {
    $resultNames = @(
        ($outputStem + '.zh.' + $kind + '.pdf')
        ($outputStem + '.no_watermark.zh.' + $kind + '.pdf')
    )
    $result = $resultNames | ForEach-Object { Join-Path $Output $_ } | Where-Object { (Test-Path -LiteralPath $_) -and (Get-Item -LiteralPath $_).LastWriteTime -ge $translateStarted } | Select-Object -First 1
    if (-not $result) {
        throw "没有生成本次 $kind 翻译结果。"
    }
    Write-Output $result
}
