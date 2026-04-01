$AppDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ExePath = Join-Path $AppDir "dist\rapid_viewer.exe"
$IcoPath = Join-Path $AppDir "rapid_viewer.ico"
$LnkPath = Join-Path $AppDir "SURPHASE Rapid Viewer.lnk"
$SmLnk   = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\SURPHASE Rapid Viewer.lnk"

# 바로가기 생성
$WS  = New-Object -ComObject WScript.Shell
$LNK = $WS.CreateShortcut($LnkPath)
$LNK.TargetPath       = $ExePath
$LNK.WorkingDirectory = $AppDir
$LNK.Description      = "SURPHASE ABB RAPID Toolpath Viewer"
$LNK.IconLocation     = "$IcoPath,0"
$LNK.WindowStyle      = 1
$LNK.Save()
Write-Host "Shortcut: $LnkPath" -ForegroundColor Cyan

# 시작 메뉴 복사
Copy-Item $LnkPath $SmLnk -Force
Write-Host "Start Menu: $SmLnk" -ForegroundColor Cyan

# 레지스트리 AppUserModelID
$RegBase = "HKCU:\SOFTWARE\Classes\Applications\rapid_viewer.exe"
New-Item -Path $RegBase -Force | Out-Null
Set-ItemProperty -Path $RegBase -Name "FriendlyAppName" -Value "SURPHASE Rapid Viewer"
Set-ItemProperty -Path $RegBase -Name "AppUserModelID"  -Value "SURPHASE.RapidViewer.v1"
$OpenKey = "$RegBase\shell\open\command"
New-Item -Path $OpenKey -Force | Out-Null
Set-ItemProperty -Path $OpenKey -Name "(Default)" -Value "`"$ExePath`""
Write-Host "Registry: OK" -ForegroundColor Green

Write-Host ""
Write-Host "완료. Win키 → 'SURPHASE' 검색 → 우클릭 → 시작 화면에 고정" -ForegroundColor Yellow
