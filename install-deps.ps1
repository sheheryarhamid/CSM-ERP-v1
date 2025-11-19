# Powershell script to set up backend Python venv and frontend node deps
# Usage: Open PowerShell (as user), cd to repo root, then `.	ools\install-deps.ps1`

param(
    [switch]$SkipFrontend
)

Write-Host "== Central ERP Hub — Dependency installer =="

# 1) Ensure Python exists and is latest available (user's system)
Write-Host "Checking Python version..."
python --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python is not found in PATH. Install Python 3.11+ and re-run this script." -ForegroundColor Red
    exit 1
}

$pyver = (python --version) -replace "Python ", ""
Write-Host "Found Python: $pyver"

# Create venv
if (-Not (Test-Path -Path ".\venv")) {
    Write-Host "Creating virtual environment at .\venv"
    python -m venv .\venv
}

# Activate venv for the current PowerShell session
Write-Host "Activating venv..."
. .\venv\Scripts\Activate.ps1

Write-Host "Upgrading pip..."
python -m pip install --upgrade pip

# Install backend requirements
if (Test-Path -Path ".\requirements.txt") {
    Write-Host "Installing backend Python packages from requirements.txt"
    pip install -r .\requirements.txt
} else {
    Write-Host "No requirements.txt found in repo root." -ForegroundColor Yellow
}

if (-not $SkipFrontend) {
    # 2) Frontend: check for node
    Write-Host "\nChecking Node.js and npm versions..."
    node --version 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Node.js is not found in PATH. Install Node (LTS) and re-run this script." -ForegroundColor Red
        exit 1
    }
    npm --version

    # Install frontend deps
    if (Test-Path -Path ".\frontend\package.json") {
        Write-Host "Installing frontend dependencies (npm install) in ./frontend"
        Push-Location .\frontend
        npm install
        Pop-Location
    } else {
        Write-Host "No frontend/package.json found." -ForegroundColor Yellow
    }
}

Write-Host "\nDone. To activate the Python venv later, run: . .\\venv\\Scripts\\Activate.ps1"
Write-Host "Start backend (dev): `uvicorn hub.main:app --reload` (example)`"
Write-Host 'Start frontend (dev): npm --prefix ./frontend run dev'
