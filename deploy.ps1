# PKB Material Confirmation System - Deployment Script (v2.6)

$sourceDir = "C:\Users\carlo\Desktop\Programing\Python\MAterialConfirmation"
$destDir = "C:\Users\carlo\Carpet Wagon\Bath PC - PKB Material Confirmation System"

# Ensure destination exists
if (!(Test-Path "$destDir")) {
    Write-Host "Creating destination directory..."
    New-Item -ItemType Directory -Path "$destDir" -Force
}

Write-Host "--------------------------------------------------"
Write-Host "Starting Deployment of v2.6"
Write-Host "Source: $sourceDir"
Write-Host "Target: $destDir"
Write-Host "--------------------------------------------------"

# 1. Copy EXE
$exeName = "PKB Material Confirmation System_v2.6.exe"
$sourceExe = Join-Path $sourceDir "dist\$exeName"
$targetExe = Join-Path $destDir "PKB Material Confirmation System.exe"

if (Test-Path $sourceExe) {
    Write-Host "Copying Executable..."
    Copy-Item "$sourceExe" -Destination "$targetExe" -Force
} else {
    Write-Host "Error: Could not find $sourceExe"
    exit
}

# 2. Copy Database Folder
$sourceDb = Join-Path $sourceDir "database"
$targetDb = Join-Path $destDir "database"

if (Test-Path $sourceDb) {
    Write-Host "Syncing Database..."
    if (!(Test-Path $targetDb)) { New-Item -ItemType Directory -Path $targetDb -Force | Out-Null }
    Copy-Item -Path "$sourceDb\*" -Destination "$targetDb" -Recurse -Force
}

# 3. Copy Documentation
Write-Host "Updating Documentation..."
$docs = @("Ollama.md", "README.md", "ROADMAP.md", "SYSTEM_USER_GUIDE.md")
foreach ($doc in $docs) {
    $docPath = Join-Path $sourceDir $doc
    if (Test-Path $docPath) {
        Copy-Item "$docPath" -Destination "$destDir" -Force
    }
}

# 4. Ensure Operational Folders Exist
Write-Host "Verifying Operational Folders..."
$folders = @("sessions", "logs", "output")
foreach ($folder in $folders) {
    $folderPath = Join-Path $destDir $folder
    if (!(Test-Path $folderPath)) {
        New-Item -ItemType Directory -Path $folderPath -Force | Out-Null
    }
}

Write-Host "--------------------------------------------------"
Write-Host "Deployment Successful! v2.6 is now live."
Write-Host "--------------------------------------------------"
