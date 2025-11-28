<#
Package environment-only ZIP containing:
- `env_installer.ps1`
- `wheels/` directory with downloaded wheels

Usage:
  .\build_env_package.ps1 -OutputZip "C:\temp\CentralERP_Env_Package.zip"
#>

param(
    [string]$OutputZip = "$env:TEMP\\CentralERP_Env_Package.zip",
    [string]$WheelsDir = "$(Join-Path $PSScriptRoot 'wheels')"
)

$RepoRoot = (Get-Location).ProviderPath
Write-Host "Building environment package from: $RepoRoot"

$staging = Join-Path $env:TEMP "central_erp_env_staging"
if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
New-Item -ItemType Directory -Path $staging | Out-Null

# Copy env_installer
Copy-Item -Path (Join-Path $RepoRoot 'installer\\env_installer.ps1') -Destination (Join-Path $staging 'env_installer.ps1') -Force

# Copy wheels if they exist
if (Test-Path $WheelsDir) {
    Write-Host "Including wheels from: $WheelsDir"
    Copy-Item -Path (Join-Path $WheelsDir '*') -Destination (Join-Path $staging 'wheels') -Recurse -Force
} else {
    Write-Warn "Wheels directory not found. Run build_wheels.ps1 first to populate wheels/"
}

if (Test-Path $OutputZip) { Remove-Item $OutputZip -Force }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($staging, $OutputZip)
Write-Host "Created env package: $OutputZip"
Remove-Item -Recurse -Force $staging
