param (
    [switch]$nobuild
)

# PKB Material Confirmation System - Deployment Script (v3.1)

$sourceDir = "C:\Users\carlo\Desktop\Programing\Python\MAterialConfirmation"
$destDir = "C:\Users\carlo\Carpet Wagon\Bath PC - PKB Material Confirmation System"

Write-Host "--------------------------------------------------"
Write-Host "Starting Deployment of v3.1"
Write-Host "Source: $sourceDir"
Write-Host "Target: $destDir"
if ($nobuild) { Write-Host "Build Mode: SKIPPED (--nobuild)" }
Write-Host "--------------------------------------------------"

# 0. Build Executable
if (!$nobuild) {
    Write-Host "Step 0: Building Executable with PyInstaller..."
    # Using python -m PyInstaller to ensure it uses the current environment's installer
    python -m PyInstaller gui_main.spec --noconfirm
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: PyInstaller build failed. Deployment aborted."
        exit
    }
}

# 1. Copy EXE
$exeName = "PKB Material Confirmation System_v3.1.exe"
$sourceExe = Join-Path $sourceDir "dist\$exeName"
$targetExe = Join-Path $destDir "PKB Material Confirmation System.exe"

if (Test-Path $sourceExe) {
    Write-Host "Step 1: Copying Executable..."
    Copy-Item "$sourceExe" -Destination "$targetExe" -Force
} else {
    Write-Host "Error: Could not find $sourceExe"
    exit
}


# 3. Copy Documentation

Write-Host "Step 3: Updating Documentation..."
$docs = @("Ollama.md", "README.md", "ROADMAP.md", "USER_GUIDE.md", "ADMIN_GUIDE.md")
foreach ($doc in $docs) {
    $docPath = Join-Path $sourceDir $doc
    if (Test-Path $docPath) {
        Copy-Item "$docPath" -Destination "$destDir" -Force
    }
}

Write-Host "--------------------------------------------------"
Write-Host "Deployment Successful! v3.1 is now live."
Write-Host "--------------------------------------------------"
