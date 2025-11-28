<#
Build helper: packages current repository into a portable ZIP for transfer.

Usage (developer machine):
    .\build_installer.ps1 -OutputZip "C:\temp\CentralERP_Portable.zip"

What it does:
- Packages the repository (excluding .git and .venv) into a ZIP
- Adds the `install_portable.ps1` at top-level of the archive (it's already in installer/)

Note: For a true single-EXE installer use Inno Setup or NSIS to wrap the ZIP and invoke `install_portable.ps1`.
#>

param(
    [string]$OutputZip = "$env:TEMP\\CentralERP_Portable.zip"
)

$RepoRoot = (Get-Location).ProviderPath
Write-Host "Packaging repository from: $RepoRoot"

$staging = Join-Path $env:TEMP "central_erp_portable_staging"
if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
New-Item -ItemType Directory -Path $staging | Out-Null

$exclude = @('.git', '.venv', 'installer\\output', 'dev\\test_data')
Get-ChildItem -Path $RepoRoot -Force | Where-Object { $exclude -notcontains $_.Name } | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination (Join-Path $staging $_.Name) -Recurse -Force
}

# Ensure top-level installer script is present
Copy-Item -Path (Join-Path $RepoRoot 'installer\\install_portable.ps1') -Destination (Join-Path $staging 'install_portable.ps1') -Force

# Build wheel cache into staging if available (call builder script)
$wheelsBuilder = Join-Path $RepoRoot 'installer\\build_wheels.ps1'
if (Test-Path $wheelsBuilder) {
    Write-Host "Running wheel builder to populate offline wheels..."
    try {
        # Create target wheels dir inside staging
        $wheelsTarget = Join-Path $staging 'wheels'
        New-Item -ItemType Directory -Path $wheelsTarget | Out-Null
        & powershell -NoProfile -ExecutionPolicy Bypass -File $wheelsBuilder -OutputDir $wheelsTarget
        # Copy built wheels into staging (builder already downloaded into outputdir)
        if ((Get-ChildItem -Path $wheelsTarget -Recurse | Measure-Object).Count -gt 0) {
            Write-Host "Wheels added to staging for offline install."
        } else {
            Write-Warn "Wheel builder ran but no files found in $wheelsTarget"
        }
    } catch {
        Write-Warn "Wheel builder failed: $_"
    }
} else {
    Write-Warn "Wheel builder script not present; proceeding without bundled wheels."
}

if (Test-Path $OutputZip) { Remove-Item $OutputZip -Force }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($staging, $OutputZip)

Write-Host "Created portable zip: $OutputZip"
Remove-Item -Recurse -Force $staging
