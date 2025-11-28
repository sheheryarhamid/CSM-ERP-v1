<#
Helper to compile the Inno Setup installer if Inno Setup is installed on the build machine.

Usage:
  .\build_inno_installer.ps1 -SourceRoot <repo-root> -OutputDir <where-to-put-installer>

This script looks for ISCC.exe at the default Inno Setup install location
and invokes it to build `central_erp_installer.iss`.
#>

param(
  [string]$SourceRoot = (Get-Location).ProviderPath,
  [string]$OutputDir = "$(Join-Path $env:TEMP 'inno_build')",
  [string]$ISCCPath = 'C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe'
)

Write-Host "This script has moved to 'installer/inno/build_inno_installer.ps1'. Running that script instead."
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'inno\\build_inno_installer.ps1') -SourceRoot $SourceRoot -OutputDir $OutputDir -ISCCPath $ISCCPath
Invoke-Expression $cmd

Write-Host "If compilation succeeded, check $OutputDir for the installer EXE."
