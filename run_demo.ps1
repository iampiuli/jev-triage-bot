# Runs the triage pipeline step by step, for screen recording.
# Usage: .\run_demo.ps1            (uses saved results\issues.json)
#        .\run_demo.ps1 -Fetch     (re-fetches 15 fresh issues first; optional -Repo owner/name)
param([switch]$Fetch, [string]$Repo = "facebook/react")

$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
Set-Location $PSScriptRoot

function Step($title, $script, $args_ = @()) {
    Write-Host ""
    Write-Host "=== $title ===" -ForegroundColor Cyan
    Write-Host "> python $script $($args_ -join ' ')" -ForegroundColor DarkGray
    & $py $script @args_
    if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: $script" -ForegroundColor Red; exit 1 }
    Start-Sleep -Seconds 2
}

Clear-Host
if ($Fetch) { Step "1/4 Fetch open issues from $Repo" "fetch_issues.py" @($Repo) }
Step "Jev (TypeSafe System One) triage" "triage_jev.py"
Step "LLM triage" "triage_llm.py"
Step "Side-by-side comparison" "compare.py"
Write-Host ""
Write-Host "Done. Results saved in results\" -ForegroundColor Green
