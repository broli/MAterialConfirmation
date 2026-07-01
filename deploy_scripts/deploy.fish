#!/usr/bin/env fish

# PKB Material Confirmation System - Deployment Script [Linux]

set NOBUILD false

for arg in $argv
    if test "$arg" = "--nobuild"
        set NOBUILD true
    end
end

set_color cyan
echo "--------------------------------------------------"
echo "Starting Deployment (Linux)"
if test "$NOBUILD" = "true"
    set_color yellow
    echo "Build Mode: SKIPPED (--nobuild)"
    set_color cyan
end
echo "--------------------------------------------------"
set_color normal

# 0. Build Executable
if test "$NOBUILD" = "false"
    # Ensure it's called from the script's directory so relative paths work if needed
    # Or just assume the user runs it from the project root.
    ./deploy_scripts/build.fish
    if test $status -ne 0
        set_color red
        echo "Error: Build failed. Deployment aborted."
        set_color normal
        exit 1
    end
end

# Verify the executable exists before trying to copy
# Find the executable dynamically
set EXE_PATH (ls ./dist/PKB\ Material\ Confirmation\ System_v* 2>/dev/null | head -n 1)

if test -z "$EXE_PATH"; or not test -f "$EXE_PATH"
    set_color red
    echo "Deployment aborted because the build failed or the executable was not found."
    set_color normal
    exit 1
end

set EXE_NAME (basename "$EXE_PATH")
set TARGET_NAME "PKB Material Confirmation System"

set appDir "$HOME/.local/share/PKB Material Confirmation System"
set appsDir "$HOME/.local/share/applications"

set_color cyan
echo "Deploying local application to $appDir..."
set_color normal

# Create directories if they don't exist
mkdir -p "$appDir"
mkdir -p "$appsDir"

# 1. Local XDG Deployment
# Copy the executable
cp -f "$EXE_PATH" "$appDir/$TARGET_NAME"

if test $status -ne 0
    set_color red
    echo "Failed to copy the executable."
    set_color yellow
    echo "Make sure the application is closed before deploying."
    set_color normal
    exit 1
end

# Copy the documentation locally
set DOCS "Ollama.md" "README.md" "ROADMAP.md" "USER_GUIDE.md" "ADMIN_GUIDE.md"
for doc in $DOCS
    if test -f "./$doc"
        cp -f "./$doc" "$appDir/"
    end
end

# Copy the icon
if test -f "./icon/Icon_512.png"
    cp -f "./icon/Icon_512.png" "$appDir/pkb-material-confirmation.png"
end

# Create the .desktop file
set desktopFile "$appsDir/pkb-material-confirmation.desktop"
set_color cyan
echo "Creating desktop entry at $desktopFile..."
set_color normal

echo "[Desktop Entry]
Version=1.0
Name=PKB Material Confirmation System
Comment=Manage and confirm materials for projects
Exec=\"$appDir/$TARGET_NAME\"
Path=$appDir
Icon=$appDir/pkb-material-confirmation.png
Terminal=false
Type=Application
Categories=Utility;Office;" > "$desktopFile"

chmod +x "$desktopFile"

# Update desktop database
if command -v update-desktop-database > /dev/null 2>&1
    update-desktop-database "$appsDir"
end

# 2. Rclone Sync to SharePoint
set_color cyan
echo "Syncing to SharePoint (rclone)..."
set_color normal
# Create a temporary staging directory to ensure a clean sync
set TMP_STAGE "/tmp/pkb_mc_stage"
mkdir -p "$TMP_STAGE"
rm -rf "$TMP_STAGE"/*
cp -f "$EXE_PATH" "$TMP_STAGE/$TARGET_NAME"
# Copy the documentation locally
for doc in $DOCS
    if test -f "./$doc"
        cp -f "./$doc" "$TMP_STAGE/"
    end
end

# Copy the Windows executable if it was pulled via git
set WINDOWS_EXE "./windows_build/PKB Material Confirmation System.exe"
if test -f "$WINDOWS_EXE"
    set_color cyan
    echo "Found Windows executable, including in sync..."
    set_color normal
    cp -f "$WINDOWS_EXE" "$TMP_STAGE/"
end

# Perform the sync
rclone sync "$TMP_STAGE" "PKBspBathPC:PKB Material Confirmation System" --progress
if test $status -ne 0
    set_color red
    echo "Error: Rclone sync to SharePoint failed."
    set_color normal
    exit 1
end

# Cleanup
rm -rf "$TMP_STAGE"

set_color green
echo "--------------------------------------------------"
echo "Deployment Successful!"
echo "Local Executable: $appDir/$TARGET_NAME"
echo "SharePoint Sync Complete."
echo "--------------------------------------------------"
set_color normal
