$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvPython = Join-Path $RepositoryRoot ".venv\Scripts\python.exe"
$Requirements = Join-Path $RepositoryRoot "requirements.txt"
$WebRoot = Join-Path $RepositoryRoot "web"

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command,
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command exited with code $LASTEXITCODE."
    }
}

try {
    Set-Location $RepositoryRoot

    if (-not (Test-Path $VenvPython)) {
        $SystemPython = Get-Command python -ErrorAction Stop
        Write-Host "[setup] Creating .venv with $($SystemPython.Source)"
        Invoke-Native $SystemPython.Source "-m" "venv" (Join-Path $RepositoryRoot ".venv")
    }

    Write-Host "[setup] Installing Python requirements in .venv"
    Invoke-Native $VenvPython "-m" "pip" "install" "--quiet" "--disable-pip-version-check" "--upgrade" "-r" $Requirements

    $Node = Get-Command node -ErrorAction Stop
    $Npm = Get-Command npm -ErrorAction Stop
    Write-Host "[setup] Node $(& $Node.Source --version), npm $(& $Npm.Source --version)"

    Write-Host "[1/4] Running Python pipeline"
    Invoke-Native $VenvPython (Join-Path $RepositoryRoot "run_pipeline.py")

    Write-Host "[2/4] Checking generated outputs"
    Invoke-Native $VenvPython (Join-Path $RepositoryRoot "tests\smoke_check_outputs.py")

    Write-Host "[3/4] Exporting web dashboard data"
    Invoke-Native $VenvPython (Join-Path $RepositoryRoot "scripts\export_web_data.py")

    Set-Location $WebRoot
    if (-not (Test-Path (Join-Path $WebRoot "node_modules"))) {
        Write-Host "[setup] Installing web dependencies"
        Invoke-Native $Npm.Source "install"
    }

    Write-Host "[4/4] Building React dashboard"
    Invoke-Native $Npm.Source "run" "build"
    Write-Host ""
    Write-Host "Production build completed successfully."
}
catch {
    Write-Host ""
    Write-Error "Production build failed: $($_.Exception.Message)"
    exit 1
}
