# Create a Desktop shortcut for PyScrapr with the spider icon.
# Run with: powershell -ExecutionPolicy Bypass -File create-shortcut.ps1

$ws = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$lnkPath = Join-Path $desktop 'PyScrapr.lnk'
$projectRoot = 'C:\laragon\www\scraper_app'

$lnk = $ws.CreateShortcut($lnkPath)
$lnk.TargetPath = Join-Path $projectRoot 'run-pyscrapr.bat'
$lnk.WorkingDirectory = $projectRoot
$lnk.IconLocation = (Join-Path $projectRoot 'assets\spider.ico')
$lnk.Description = 'PyScrapr - Modular web scraping toolkit'
$lnk.WindowStyle = 1
$lnk.Save()

Write-Host "[OK] Shortcut created: $lnkPath"
Write-Host "     Target : $($lnk.TargetPath)"
Write-Host "     Icon   : $($lnk.IconLocation)"
