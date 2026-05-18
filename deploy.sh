#!/bin/bash

# PKB Material Confirmation System - Deployment Script (v4.0) [Linux]

NOBUILD=false

for arg in "$@"; do
    if [ "$arg" == "--nobuild" ]; then
        NOBUILD=true
    fi
done

SOURCE_DIR="$(pwd)"
DEST_DIR="/home/carlos/Carpet Wagon/Bath PC - PKB Material Confirmation System"

echo "--------------------------------------------------"
echo "Starting Deployment of v4.0 (Linux)"
echo "Source: $SOURCE_DIR"
echo "Target: $DEST_DIR"
if [ "$NOBUILD" = true ]; then
    echo "Build Mode: SKIPPED (--nobuild)"
fi
echo "--------------------------------------------------"

# Ensure destination exists
mkdir -p "$DEST_DIR"

# 0. Build Executable
if [ "$NOBUILD" = false ]; then
    echo "Step 0: Building Executable with PyInstaller..."
    ./.venv/bin/python -m PyInstaller gui_main.spec --noconfirm
    if [ $? -ne 0 ]; then
        echo "Error: PyInstaller build failed. Deployment aborted."
        exit 1
    fi
fi

# 1. Copy Executable
EXE_NAME="PKB Material Confirmation System_v4.0"
SOURCE_EXE="$SOURCE_DIR/dist/$EXE_NAME"
TARGET_EXE="$DEST_DIR/PKB Material Confirmation System"

if [ -f "$SOURCE_EXE" ]; then
    echo "Step 1: Copying Executable..."
    cp -f "$SOURCE_EXE" "$TARGET_EXE"
else
    echo "Error: Could not find $SOURCE_EXE"
    exit 1
fi

# 2. Copy Documentation
echo "Step 2: Updating Documentation..."
DOCS=("Ollama.md" "README.md" "ROADMAP.md" "USER_GUIDE.md" "ADMIN_GUIDE.md")

for doc in "${DOCS[@]}"; do
    if [ -f "$SOURCE_DIR/$doc" ]; then
        cp -f "$SOURCE_DIR/$doc" "$DEST_DIR/"
    fi
done

echo "--------------------------------------------------"
echo "Deployment Successful! v4.0 is now live on Linux."
echo "--------------------------------------------------"
