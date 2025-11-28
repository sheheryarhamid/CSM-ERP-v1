<#
Environment-only Installer for Central ERP Hub

This script is intended to be the first package in the installation wizard.
It performs the following:
- Ensures Python 3.11+ is installed (downloads silently if needed)
- Creates a central wheels cache at `C:\ProgramData\CentralERPHub\wheels` (or user-specified)
- Creates a reusable virtualenv template at `C:\ProgramData\CentralERPHub\env_template` installed from wheels

After this completes, the main `install_portable.ps1` can copy the `env_template` into the application
install directory to avoid re-downloading packages and speed up offline installs.

Usage on target machine (elevated PowerShell):
  Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
  .\env_installer.ps1 -TargetRoot "C:\ProgramData\CentralERPHub"

If wheels are bundled in the same package, the script will detect them in the current directory under `wheels\`.
#>

param(
    [string]$TargetRoot = "C:\ProgramData\CentralERPHub",
    [string]$WheelsSource = "$(Join-Path $PSScriptRoot 'wheels')",
    [switch]$Force
)

function Write-Info { param($m) Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Write-Warn { param($m) Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Write-Err { param($m) Write-Host "[ERROR] $m" -ForegroundColor Red }

# Simple Ensure-Python function (copies logic from install_portable)
function Ensure-Python {
    Write-Info "Checking for Python 3.11+ on PATH..."
    try { $pyVersion = & python --version 2>&1 } catch { $pyVersion = $null }
    if ($pyVersion -and $pyVersion -match "Python\s+([0-9]+)\.([0-9]+)") {
        $major = [int]$Matches[1]; $minor=[int]$Matches[2]
        if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 11)) { Write-Info "Found system Python: $pyVersion"; return "python" }
    }

    # Download Python installer and run silently
    $pythonUrl = 'https://www.python.org/ftp/python/3.11.6/python-3.11.6-amd64.exe'
    $installer = Join-Path $env:TEMP "python-installer.exe"
    Write-Info "Downloading Python installer..."
    Invoke-WebRequest -Uri $pythonUrl -OutFile $installer -UseBasicParsing
    Start-Process -FilePath $installer -ArgumentList '/quiet', 'InstallAllUsers=1', 'PrependPath=1', 'Include_pip=1' -Wait
    Remove-Item $installer -Force -ErrorAction SilentlyContinue
    try { $pyVersion = & python --version 2>&1; Write-Info "Installed Python: $pyVersion"; return "python" } catch { throw "Python installation failed." }
}

$pythonCmd = Ensure-Python

# Prepare target directories
if (-not (Test-Path $TargetRoot)) { New-Item -ItemType Directory -Path $TargetRoot -Force | Out-Null }
$wheelsTarget = Join-Path $TargetRoot 'wheels'
$envTemplate = Join-Path $TargetRoot 'env_template'
if (-not (Test-Path $wheelsTarget)) { New-Item -ItemType Directory -Path $wheelsTarget | Out-Null }

Write-Info "Wheels source: $WheelsSource"
if (Test-Path $WheelsSource) {
    Write-Info "Copying bundled wheels to $wheelsTarget"
    Copy-Item -Path (Join-Path $WheelsSource '*') -Destination $wheelsTarget -Force -Recurse
} else {
    Write-Warn "No bundled wheels found at $WheelsSource. If you are offline, the next step will fail."
}

# Create or refresh env template
if (Test-Path $envTemplate -and -not $Force) {
    Write-Warn "Env template already exists at $envTemplate. Use -Force to recreate."
} else {
    if (Test-Path $envTemplate) { Remove-Item -Recurse -Force $envTemplate }
    Write-Info "Creating virtualenv template at $envTemplate"
    & python -m venv $envTemplate
    $templatePython = Join-Path $envTemplate 'Scripts\python.exe'
    $templatePip = Join-Path $envTemplate 'Scripts\pip.exe'
    & $templatePython -m pip install --upgrade pip

    $req = Join-Path (Split-Path -Parent $PSScriptRoot) 'requirements.txt'
    if (-not (Test-Path $req)) { $req = Join-Path (Get-Location) 'requirements.txt' }
    if (Test-Path $wheelsTarget -and (Get-ChildItem $wheelsTarget | Measure-Object).Count -gt 0) {
        Write-Info "Installing requirements into env template from local wheels"
        & $templatePip install --no-index --find-links $wheelsTarget -r $req
    } else {
        Write-Info "No wheels available locally; installing from PyPI into env template"
        & $templatePip install -r $req
    }
}

Write-Info "Environment installation complete. Env template located at: $envTemplate"
Write-Host "Next: Run installer to deploy the application and copy the env template into the app folder." -ForegroundColor Green
