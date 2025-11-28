; Central ERP Hub Installer (Inno Setup Script)
; Moved into installer/inno/ for optional builds

[Setup]
AppName=Central ERP Hub
AppVersion=1.3.0
DefaultDirName={pf}\CentralERPHub
DefaultGroupName=Central ERP Hub
Compression=lzma2
SolidCompression=yes
OutputBaseFilename=CentralERP_Installer
PrivilegesRequired=admin

[Files]
; Include both packaged ZIPs so the installer can run offline
Source: "..\\CentralERP_Env_Package.zip"; DestDir: "{tmp}"; Flags: ignoreversion
Source: "..\\CentralERP_Portable.zip"; DestDir: "{tmp}"; Flags: ignoreversion

[Icons]
Name: "{group}\Central ERP Hub Documentation"; Filename: "{app}\dev\\frontend\\index.html"; Flags: noadvice

[Run]
; 1) Run environment installer from the extracted env package
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command \"Expand-Archive -Path '{tmp}\\CentralERP_Env_Package.zip' -DestinationPath '{tmp}\\env_pkg' -Force; Start-Sleep -Seconds 1; & '{tmp}\\env_pkg\\env_installer.ps1' -TargetRoot 'C:\\ProgramData\\CentralERPHub' -Force\""; Flags: waituntilterminated

; 2) After env installer completes, run the main portable installer
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command \"Expand-Archive -Path '{tmp}\\CentralERP_Portable.zip' -DestinationPath '{tmp}\\app_pkg' -Force; Start-Sleep -Seconds 1; & '{tmp}\\app_pkg\\install_portable.ps1' -InstallDir '{pf}\\CentralERPHub'\""; Flags: shellexec waituntilterminated

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
