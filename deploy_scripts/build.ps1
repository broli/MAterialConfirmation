<#
.SYNOPSIS
Builds the PKB Material Confirmation System on Windows using PyInstaller.
#>

Write-Host "--------------------------------------------------" -ForegroundColor Cyan
Write-Host "Starting Build Process (Windows)..." -ForegroundColor Cyan
Write-Host "--------------------------------------------------" -ForegroundColor Cyan

# Remove old executable if it exists
$oldExeFiles = Get-ChildItem -Path ".\dist" -Filter "PKB Material Confirmation System_v*.exe" -ErrorAction SilentlyContinue
foreach ($file in $oldExeFiles) {
    Write-Host "Cleaning up old build: $($file.Name)" -ForegroundColor Yellow
    Remove-Item $file.FullName -Force
}

# Run PyInstaller
Write-Host "Running PyInstaller..." -ForegroundColor Cyan
& .\.venv\Scripts\python.exe -m PyInstaller gui_main.spec --noconfirm

if ($LASTEXITCODE -eq 0) {
    Write-Host "--------------------------------------------------" -ForegroundColor Green
    Write-Host "Build Successful! Executable is in the 'dist' folder." -ForegroundColor Green
    Write-Host "--------------------------------------------------" -ForegroundColor Green
} else {
    Write-Host "--------------------------------------------------" -ForegroundColor Red
    Write-Host "Error: Build failed." -ForegroundColor Red
    Write-Host "--------------------------------------------------" -ForegroundColor Red
    exit $LASTEXITCODE
}
