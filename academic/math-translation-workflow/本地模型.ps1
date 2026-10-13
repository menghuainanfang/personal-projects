param([ValidateSet('start', 'pull', 'status', 'stop')][string]$Action = 'status')
$ErrorActionPreference = 'Stop'
$ollamaExe = Join-Path $PSScriptRoot 'tools/ollama/ollama.exe'
$modelState = Join-Path $PSScriptRoot 'state/ollama'
$modelName = 'qwen3:4b-instruct'
$env:OLLAMA_HOST = '127.0.0.1:11435'
$env:OLLAMA_MODELS = Join-Path $modelState 'models'
$env:OLLAMA_CONTEXT_LENGTH = '8192'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_MAX_LOADED_MODELS = '1'
$env:OLLAMA_KEEP_ALIVE = '10m'
New-Item -ItemType Directory -Path $modelState -Force | Out-Null
$pidFile = Join-Path $modelState 'server.pid'
switch ($Action) {
    'start' {
        try {
            $null = Invoke-RestMethod 'http://127.0.0.1:11435/api/version'
            Write-Output '本地模型服务已运行。'
        } catch {
            $modelProcess = Start-Process -FilePath $ollamaExe -ArgumentList 'serve' -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $modelState 'server.stdout.log') -RedirectStandardError (Join-Path $modelState 'server.stderr.log')
            $modelProcess.Id | Set-Content -LiteralPath $pidFile
            for ($attempt = 0; $attempt -lt 20; $attempt++) {
                Start-Sleep -Seconds 1
                try {
                    $null = Invoke-RestMethod 'http://127.0.0.1:11435/api/version'
                    Write-Output '本地模型服务已启动，地址：http://127.0.0.1:11435'
                    return
                } catch {}
            }
            throw '本地模型服务尚未启动，请查看 state/ollama/server.stderr.log。'
        }
    }
    'pull' {
        & $ollamaExe pull $modelName
        if ($LASTEXITCODE -ne 0) { throw '模型下载未完成。' }
    }
    'status' {
        Invoke-RestMethod 'http://127.0.0.1:11435/api/version'
        & $ollamaExe list
        & $ollamaExe ps
    }
    'stop' {
        if (Test-Path -LiteralPath $pidFile) {
            $savedModelPid = [int](Get-Content -LiteralPath $pidFile)
            $savedModelProcess = Get-Process -Id $savedModelPid -ErrorAction SilentlyContinue
            if ($savedModelProcess -and $savedModelProcess.Path -eq $ollamaExe) {
                Stop-Process -Id $savedModelPid
            }
            Remove-Item -LiteralPath $pidFile
        }
    }
}
