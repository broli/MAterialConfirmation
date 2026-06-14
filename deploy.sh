#!/bin/bash

# PKB Material Confirmation System - Deployment Script [Linux]

NOBUILD=false

for arg in "$@"; do
    if [ "$arg" == "--nobuild" ]; then
        NOBUILD=true
    fi
done

echo -e "\e[36m--------------------------------------------------\e[0m"
echo -e "\e[36mStarting Deployment (Linux)\e[0m"
if [ "$NOBUILD" = true ]; then
    echo -e "\e[33mBuild Mode: SKIPPED (--nobuild)\e[0m"
fi
echo -e "\e[36m--------------------------------------------------\e[0m"

# 0. Build Executable
if [ "$NOBUILD" = false ]; then
    ./build.sh
    if [ $? -ne 0 ]; then
        echo -e "\e[31mError: Build failed. Deployment aborted.\e[0m"
        exit 1
    fi
fi

# Verify the executable exists before trying to copy
# Find the executable dynamically (grabbing the first match)
EXE_PATH=$(ls ./dist/PKB\ Material\ Confirmation\ System_v* 2>/dev/null | head -n 1)

if [ -z "$EXE_PATH" ] || [ ! -f "$EXE_PATH" ]; then
    echo -e "\e[31mDeployment aborted because the build failed or the executable was not found.\e[0m"
    exit 1
fi

EXE_NAME=$(basename "$EXE_PATH")
TARGET_NAME="PKB Material Confirmation System"

appDir="$HOME/.local/share/PKB Material Confirmation System"
appsDir="$HOME/.local/share/applications"

echo -e "\e[36mDeploying local application to $appDir...\e[0m"

# Create directories if they don't exist
mkdir -p "$appDir"
mkdir -p "$appsDir"

# 1. Local XDG Deployment
# Copy the executable
cp -f "./dist/$EXE_NAME" "$appDir/$TARGET_NAME"

if [ $? -ne 0 ]; then
    echo -e "\e[31mFailed to copy the executable.\e[0m"
    echo -e "\e[33mMake sure the application is closed before deploying.\e[0m"
    exit 1
fi

# Copy the documentation locally
DOCS=("Ollama.md" "README.md" "ROADMAP.md" "USER_GUIDE.md" "ADMIN_GUIDE.md")
for doc in "${DOCS[@]}"; do
    if [ -f "./$doc" ]; then
        cp -f "./$doc" "$appDir/"
    fi
done

# Copy the icon
if [ -f "./icon/Icon_512.png" ]; then
    cp -f "./icon/Icon_512.png" "$appDir/pkb-material-confirmation.png"
fi

# Create the .desktop file
desktopFile="$appsDir/pkb-material-confirmation.desktop"
echo -e "\e[36mCreating desktop entry at $desktopFile...\e[0m"

cat > "$desktopFile" << EOL
[Desktop Entry]
Version=1.0
Name=PKB Material Confirmation System
Comment=Manage and confirm materials for projects
Exec="$appDir/$TARGET_NAME"
Path=$appDir
Icon=$appDir/pkb-material-confirmation.png
Terminal=false
Type=Application
Categories=Utility;Office;
EOL

chmod +x "$desktopFile"

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$appsDir"
fi

# 2. Rclone Sync to SharePoint
echo -e "\e[36mSyncing to SharePoint (rclone)...\e[0m"
# Create a temporary staging directory to ensure a clean sync
TMP_STAGE="/tmp/pkb_mc_stage"
mkdir -p "$TMP_STAGE"
rm -rf "$TMP_STAGE/*"
cp -f "./dist/$EXE_NAME" "$TMP_STAGE/$TARGET_NAME"
# Copy the documentation locally
DOCS=("Ollama.md" "README.md" "ROADMAP.md" "USER_GUIDE.md" "ADMIN_GUIDE.md")
for doc in "${DOCS[@]}"; do
    if [ -f "./$doc" ]; then
        cp -f "./$doc" "$TMP_STAGE/"
    fi
done

# Copy the Windows executable if it was pulled via git
WINDOWS_EXE="./windows_build/PKB Material Confirmation System.exe"
if [ -f "$WINDOWS_EXE" ]; then
    echo -e "\e[36mFound Windows executable, including in sync...\e[0m"
    cp -f "$WINDOWS_EXE" "$TMP_STAGE/"
fi

# Perform the sync
rclone sync "$TMP_STAGE" "PKBspBathPC:PKB Material Confirmation System" --progress
if [ $? -ne 0 ]; then
    echo -e "\e[31mError: Rclone sync to SharePoint failed.\e[0m"
    exit 1
fi

# Cleanup
rm -rf "$TMP_STAGE"

echo -e "\e[32m--------------------------------------------------\e[0m"
echo -e "\e[32mDeployment Successful!\e[0m"
echo -e "\e[32mLocal Executable: $appDir/$TARGET_NAME\e[0m"
echo -e "\e[32mSharePoint Sync Complete.\e[0m"
echo -e "\e[32m--------------------------------------------------\e[0m"
