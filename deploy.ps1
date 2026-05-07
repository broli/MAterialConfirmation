# PKB Material Confirmation System - Deployment Script (v3.1)

$sourceDir = "C:\Users\carlo\Desktop\Programing\Python\MAterialConfirmation"
$destDir = "C:\Users\carlo\Carpet Wagon\Bath PC - PKB Material Confirmation System"

Write-Host "--------------------------------------------------"
Write-Host "Starting Deployment of v3.1"
Write-Host "Source: $sourceDir"
Write-Host "Target: $destDir"
Write-Host "--------------------------------------------------"

# 0. Build Executable
Write-Host "Step 0: Building Executable with PyInstaller..."
pyinstaller gui_main.spec --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: PyInstaller build failed. Deployment aborted."
    exit
}

# Ensure destination exists
if (!(Test-Path "$destDir")) {
    Write-Host "Creating destination directory..."
    New-Item -ItemType Directory -Path "$destDir" -Force
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

# 2. Copy Database Folder (Categories only)
$sourceDb = Join-Path $sourceDir "database"
$targetDb = Join-Path $destDir "database"

if (Test-Path $sourceDb) {
    Write-Host "Step 2: Syncing Database..."
    if (!(Test-Path $targetDb)) { New-Item -ItemType Directory -Path $targetDb -Force | Out-Null }
    # Copy categories and templates, skip assets (too large) and backups
    Copy-Item -Path "$sourceDb\categories" -Destination "$targetDb" -Recurse -Force
    Copy-Item -Path "$sourceDb\templates" -Destination "$targetDb" -Recurse -Force
}

# 3. Copy Documentation
Write-Host "Step 3: Updating Documentation..."
$docs = @("Ollama.md", "README.md", "ROADMAP.md", "SYSTEM_USER_GUIDE.md")
foreach ($doc in $docs) {
    $docPath = Join-Path $sourceDir $doc
    if (Test-Path $docPath) {
        Copy-Item "$docPath" -Destination "$destDir" -Force
    }
}

# 4. Ensure Operational Folders Exist
Write-Host "Step 4: Verifying Operational Folders..."
$folders = @("sessions", "logs", "output")
foreach ($folder in $folders) {
    $folderPath = Join-Path $destDir $folder
    if (!(Test-Path $folderPath)) {
        New-Item -ItemType Directory -Path $folderPath -Force | Out-Null
    }
}

Write-Host "--------------------------------------------------"
Write-Host "Deployment Successful! v3.1 is now live."
Write-Host "--------------------------------------------------"
