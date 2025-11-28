<#
Compile Inno Setup installer for Central ERP Hub.

Run this on a build machine that has Inno Setup 6 installed.

Usage:
  powershell -NoProfile -ExecutionPolicy Bypass -File installer\inno\build_inno_installer.ps1 -OutputDir ".\\installer\\output"
#>

param(
    [string]$SourceRoot = (Get-Location).ProviderPath,
    [string]$OutputDir = "$(Join-Path $env:TEMP 'inno_build')",
    [string]$ISCCPath = 'C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe'
)

$iss = Join-Path $SourceRoot 'installer\\inno\\central_erp_installer.iss'

if (-not (Test-Path $iss)) { Write-Error "Inno script not found at: $iss"; exit 1 }

if (-not (Test-Path $ISCCPath)) {
    Write-Error "Inno Setup compiler not found at $ISCCPath. Please install Inno Setup (https://jrsoftware.org)."
    exit 1
}

if (-not (Test-Path $OutputDir)) { New-Item -ItemType Directory -Path $OutputDir | Out-Null }

$cmd = "`"$ISCCPath`" /O`"$OutputDir`" `"$iss`""
Write-Host "Running: $cmd"
Invoke-Expression $cmd

Write-Host "If compilation succeeded, check $OutputDir for the installer EXE."
