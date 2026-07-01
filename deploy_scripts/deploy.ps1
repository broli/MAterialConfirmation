<#
.SYNOPSIS
Deploys the built Windows executable to the windows_build directory for syncing via GitHub.
#>

param (
    [switch]$NoBuild
)

Write-Host "--------------------------------------------------" -ForegroundColor Cyan
Write-Host "Starting Deployment (Windows to GitHub Bridge)" -ForegroundColor Cyan
if ($NoBuild) {
    Write-Host "Build Mode: SKIPPED (-NoBuild)" -ForegroundColor Yellow
}
Write-Host "--------------------------------------------------" -ForegroundColor Cyan

# 0. Build Executable
if (-not $NoBuild) {
    .\build.ps1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Build failed. Deployment aborted." -ForegroundColor Red
        exit 1
    }
}

# 1. Locate the executable dynamically
$exePath = Get-ChildItem -Path ".\dist" -Filter "PKB Material Confirmation System_v*.exe" | Select-Object -First 1

if ($null -eq $exePath -or -not (Test-Path $exePath.FullName)) {
    Write-Host "Deployment aborted because the build failed or the executable was not found in 'dist\'." -ForegroundColor Red
    exit 1
}

$targetName = "PKB Material Confirmation System.exe"
$targetDir = ".\windows_build"

# Ensure the windows_build directory exists
if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
}

$targetFullPath = Join-Path $targetDir $targetName

Write-Host "Copying $($exePath.Name) to $targetFullPath..." -ForegroundColor Cyan

# Copy the executable to the windows_build folder
Copy-Item -Path $exePath.FullName -Destination $targetFullPath -Force

if ($?) {
    Write-Host "--------------------------------------------------" -ForegroundColor Green
    Write-Host "Deployment Successful!" -ForegroundColor Green
    Write-Host "Windows executable is now in $targetDir ready for git commit/push." -ForegroundColor Green
    Write-Host "--------------------------------------------------" -ForegroundColor Green
} else {
    Write-Host "Failed to copy the executable. Make sure it's not currently running." -ForegroundColor Red
    exit 1
}
