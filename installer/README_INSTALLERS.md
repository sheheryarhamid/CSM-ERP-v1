# Installer Packaging and Releases

This document explains the recommended workflow for building and publishing installer artifacts for Central ERP Hub.

Why we removed ZIPs from the repository
- Large generated ZIPs (e.g. `CentralERP_Env_Package.zip`, `CentralERP_Portable.zip`) were removed to avoid repository bloat. Store these artifacts in GitHub Releases or a file storage service instead.

Recommended flow
1. Build wheels for offline install:
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File installer\build_wheels.ps1 -OutputDir installer\wheels
   ```
2. Build environment package (env installer + wheels):
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File installer\build_env_package.ps1 -OutputZip installer\CentralERP_Env_Package.zip
   ```
3. Build portable app ZIP (app + wheels):
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File installer\build_installer.ps1 -OutputZip installer\CentralERP_Portable.zip
   ```
4. (Optional) Build the Inno Setup EXE on a Windows build machine with Inno installed:
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File installer\inno\build_inno_installer.ps1 -SourceRoot (Get-Location) -OutputDir .\installer\output
   ```
   The generated EXE will be in `installer\output`.

Publishing
- Upload the generated ZIPs and/or EXE to GitHub Releases (recommended). Do NOT commit them to the repository.
- Example (GitHub CLI):
  ```powershell
  gh release create v1.3.0 installer\CentralERP_Portable.zip installer\CentralERP_Env_Package.zip --title "Central ERP Hub v1.3.0" --notes "Offline installers and wheels included"
  ```

Offline install instructions (for target machine)
1. Extract `CentralERP_Env_Package.zip` and run `env_installer.ps1` as admin to populate `C:\ProgramData\CentralERPHub\env_template`.
2. Extract `CentralERP_Portable.zip` to the desired install folder and run `install_portable.ps1` as admin. The installer will copy the `env_template` into the app `.venv`.

Notes and caveats
- Copying a `venv` between machines requires identical OS/architecture and Python minor version (e.g., Windows x64 + Python 3.11.x) to avoid incompatibilities.
- If you need cross-platform installers, build platform-specific wheels and installers for each OS.

Support
- If you'd like, I can add a GitHub Actions workflow to automatically build the ZIPs and compile the Inno EXE on a Windows runner and upload artifacts to Releases.
