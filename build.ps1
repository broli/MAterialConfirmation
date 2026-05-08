# PKB Material Confirmation System - Build Script
Write-Host "--------------------------------------------------"
Write-Host "Starting Build Process..."
Write-Host "--------------------------------------------------"

# Run PyInstaller using the current environment's python
python -m PyInstaller gui_main.spec --noconfirm

if ($LASTEXITCODE -eq 0) {
    Write-Host "--------------------------------------------------"
    Write-Host "Build Successful! Executable is in the 'dist' folder."
    Write-Host "--------------------------------------------------"
} else {
    Write-Host "--------------------------------------------------"
    Write-Host "Error: Build failed."
    Write-Host "--------------------------------------------------"
    exit $LASTEXITCODE
}
