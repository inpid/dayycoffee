$target = Join-Path $PSScriptRoot "open_tracker.bat"
$desktop = [Environment]::GetFolderPath("Desktop")
$lnk = Join-Path $desktop "생두 트래커.lnk"
$sh = New-Object -ComObject WScript.Shell
$s = $sh.CreateShortcut($lnk)
$s.TargetPath = $target
$s.WorkingDirectory = $PSScriptRoot
$s.WindowStyle = 7
$s.IconLocation = "$env:SystemRoot\System32\shell32.dll,13"
$s.Save()
Write-Host "바탕화면에 '생두 트래커' 아이콘을 만들었습니다."
