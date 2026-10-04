Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " Transparent Whiteboard - Automated Windows .exe Builder" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

Write-Host "[1/3] Installing dependencies..." -ForegroundColor Yellow
python -m pip install -r requirements.txt

Write-Host "Building TransparentWhiteboard.exe..." -ForegroundColor Yellow
python -m PyInstaller --clean -y TransparentWhiteboard.spec

$exePath = "dist\TransparentWhiteboard\TransparentWhiteboard.exe"
if (Test-Path $exePath) {
    Write-Host "[SUCCESS] $exePath created!" -ForegroundColor Green
    $run = Read-Host "Launch now? (Y/N)"
    if ($run -eq "Y" -or $run -eq "y") { Start-Process $exePath }
} else {
    Write-Host "[ERROR] $exePath not found." -ForegroundColor Red
}
