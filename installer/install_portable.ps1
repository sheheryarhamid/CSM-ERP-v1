<#
Portable Installer for Central ERP Hub

Features:
- Ensures Python 3.11+ is available (installs silently if not present)
- Creates a local virtual environment inside the install directory
- Installs dependencies from `requirements.txt`
- Generates `.env` with a secure `BLOB_KEY` if not provided
- Registers a Windows service to run the ASGI app via uvicorn

Usage (on target machine):
- Unzip the package to a folder, open an elevated PowerShell, and run:
    Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
    .\install_portable.ps1 -InstallDir "C:\Program Files\CentralERPHub"

Notes:
- The script requires Internet access to download Python and pip packages unless wheels are bundled.
- Service registration uses `sc.exe` to create a service that runs the venv python.
- For production you may want to use NSSM or create a real Windows Service wrapper.
#>

param(
    [string]$InstallDir = "$env:ProgramFiles\\CentralERPHub",
    [switch]$Force,
    [switch]$NoService
)

function Write-Info { param($m) Write-Host "[INFO]  $m" -ForegroundColor Cyan }
function Write-Warn { param($m) Write-Host "[WARN]  $m" -ForegroundColor Yellow }
function Write-Err  { param($m) Write-Host "[ERROR] $m" -ForegroundColor Red }

# Ensure running as Administrator for service install and ProgramFiles write
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
    Write-Warn "Not running as Administrator — service registration may fail."
    Write-Host "Press Enter to continue without admin (service won't be installed), or Ctrl+C to abort." -NoNewline
    Read-Host | Out-Null
}

# Normalize paths
$InstallDir = [System.IO.Path]::GetFullPath($InstallDir)
$RepoRoot = (Get-Location).ProviderPath

Write-Info "Installing to: $InstallDir"

# Step 1: Ensure Python 3.11+ is installed
function Ensure-Python {
    Write-Info "Checking for Python 3.11+ on PATH..."
    try {
        $pyVersion = & python --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $pyVersion -match "Python\s+([0-9]+)\.([0-9]+)") {
            $major = [int]$Matches[1]; $minor=[int]$Matches[2]
            if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 11)) {
                Write-Info "Found system Python: $pyVersion"
                return "python"
            }
        }
    } catch { }

    # Download and run official Python installer silently
    $pythonUrl = 'https://www.python.org/ftp/python/3.11.6/python-3.11.6-amd64.exe'
    $installer = Join-Path $env:TEMP "python-installer.exe"
    Write-Info "Downloading Python 3.11 installer to $installer"
    Invoke-WebRequest -Uri $pythonUrl -OutFile $installer -UseBasicParsing
    Write-Info "Running Python installer (silent). This requires admin rights."
    Start-Process -FilePath $installer -ArgumentList '/quiet', 'InstallAllUsers=1', 'PrependPath=1', 'Include_pip=1' -Wait
    Remove-Item $installer -Force -ErrorAction SilentlyContinue

    try {
        $pyVersion = & python --version 2>&1
        Write-Info "Installed Python: $pyVersion"
        return "python"
    } catch {
        throw "Python installation failed or not available on PATH. Please install Python 3.11+ manually."
    }
}

$pythonCmd = Ensure-Python

# Step 2: Create install directory and copy files
if (Test-Path $InstallDir) {
    if (-not $Force) {
        Write-Warn "Install directory already exists: $InstallDir"
        Write-Host "Use -Force to overwrite or choose a different install dir. Press Enter to continue and reuse existing dir." -NoNewline
        Read-Host | Out-Null
    }
} else {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

Write-Info "Copying application files to install directory..."
# Exclude `.venv` and .git
$exclude = @('.venv', '.git','dev/test_data')
Get-ChildItem -Path $RepoRoot -Force | Where-Object { $exclude -notcontains $_.Name } | ForEach-Object {
    $src = $_.FullName
    $dest = Join-Path $InstallDir $_.Name
    if (Test-Path $dest) { Remove-Item -Recurse -Force $dest -ErrorAction SilentlyContinue }
    Copy-Item -Path $src -Destination $dest -Recurse -Force
}

# Step 3: Create virtual environment inside InstallDir
$venvPath = Join-Path $InstallDir '.venv'
$sharedEnv = 'C:\ProgramData\CentralERPHub\env_template'

if (Test-Path $sharedEnv -and -not $Force) {
    Write-Info "Found shared env template at $sharedEnv — copying into install dir to reuse preinstalled packages."
    if (Test-Path $venvPath) { Remove-Item -Recurse -Force $venvPath }
    Copy-Item -Path $sharedEnv -Destination $venvPath -Recurse -Force
} else {
    if (-not (Test-Path $venvPath) -or $Force) {
        Write-Info "Creating virtual environment at $venvPath"
        & $pythonCmd -m venv $venvPath
    } else {
        Write-Info "Using existing virtual environment at $venvPath"
    }
}

$venvPython = Join-Path $venvPath 'Scripts\python.exe'
$venvPip = Join-Path $venvPath 'Scripts\pip.exe'

# Step 4: Upgrade pip and install requirements
Write-Info "Upgrading pip and installing dependencies..."
& $venvPython -m pip install --upgrade pip
if (Test-Path (Join-Path $InstallDir 'requirements.txt')) {
    # If wheels are bundled for offline install, prefer them
    $bundledWheels = Join-Path $InstallDir 'wheels'
    if (Test-Path $bundledWheels) {
        Write-Info "Detected bundled wheels. Installing from wheels directory (offline mode)."
        & $venvPip install --no-index --find-links $bundledWheels -r (Join-Path $InstallDir 'requirements.txt')
    } else {
        Write-Info "No bundled wheels detected. Installing from PyPI."
        & $venvPip install -r (Join-Path $InstallDir 'requirements.txt')
    }
} else {
    Write-Warn "requirements.txt not found in install dir. Skipping pip install."
}

# Step 5: Create .env if missing
$envFile = Join-Path $InstallDir '.env'
if (-not (Test-Path $envFile)) {
    Write-Info "Generating .env with secure BLOB_KEY"
    $b64 = & $venvPython - <<'PY'
import secrets, sys
print(secrets.token_hex(32))
PY
    Set-Content -Path $envFile -Value "BLOB_KEY=$b64`nLOG_LEVEL=INFO`n"
} else {
    Write-Info ".env already exists, leaving it intact"
}

# Step 6: Create Windows service to run the app (optional)
$svcName = 'CentralERPHub'
$svcBin = "`"$venvPython`" -m uvicorn hub.main:app --host 127.0.0.1 --port 8000"

if (-not $NoService) {
    Write-Info "Registering Windows service '$svcName'"
    try {
        # Remove existing service if present
        sc.exe query $svcName > $null 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Warn "Service $svcName already exists. Attempting to stop and delete."
            sc.exe stop $svcName | Out-Null
            sc.exe delete $svcName | Out-Null
            Start-Sleep -Seconds 2
        }
    } catch { }

    $createCmd = "sc.exe create `"$svcName`" binPath= `"$svcBin`" start= auto DisplayName= `"Central ERP Hub`""
    Write-Info "Running: $createCmd"
    Invoke-Expression $createCmd

    Write-Info "Starting service $svcName"
    sc.exe start $svcName | Out-Null
    Start-Sleep -Seconds 3
    sc.exe query $svcName
} else {
    Write-Info "Service creation skipped (NoService specified)."
}

Write-Info "Installation complete."
Write-Info "Start the dashboard: http://127.0.0.1:8000/docs"
Write-Info "Open the web UI (static): $InstallDir\\dev\\frontend\\index.html (You may serve it via Python HTTP server or configure IIS)"

Write-Host "Done." -ForegroundColor Green
