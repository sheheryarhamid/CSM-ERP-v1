<#
Download all wheels for the project's requirements into a local folder for offline installation.

Usage:
    .\build_wheels.ps1 -OutputDir "C:\temp\central_wheels"

This script requires Python and pip available on the PATH.
It uses `pip download -r requirements.txt -d <outputdir>` to collect wheels.
#>

param(
    [string]$OutputDir = "$(Join-Path $PSScriptRoot 'wheels')"
)

function Write-Info { param($m) Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Write-Warn { param($m) Write-Host "[WARN] $m" -ForegroundColor Yellow }

if (-not (Test-Path $OutputDir)) { New-Item -ItemType Directory -Path $OutputDir | Out-Null }

$req = Join-Path (Resolve-Path "..\..\") 'requirements.txt'
if (-not (Test-Path $req)) { $req = Join-Path (Get-Location) 'requirements.txt' }
if (-not (Test-Path $req)) { Write-Err "requirements.txt not found. Run this from the repo root or provide a requirements file."; exit 1 }

Write-Info "Downloading wheels to: $OutputDir"

# Use pip download to fetch wheels (prefer binary wheels)
try {
    & python -m pip download -r $req -d $OutputDir
    Write-Info "Wheels downloaded successfully."
} catch {
    Write-Warn "pip download failed: $_"
    exit 1
}

Write-Info "Completed wheel collection."
