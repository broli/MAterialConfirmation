#!/bin/bash

# PKB Material Confirmation System - Build Script [Linux]
echo "--------------------------------------------------"
echo "Starting Build Process (Linux)..."
echo "--------------------------------------------------"

# Run PyInstaller using the virtual environment's python
./.venv/bin/python -m PyInstaller gui_main.spec --noconfirm

if [ $? -eq 0 ]; then
    echo "--------------------------------------------------"
    echo "Build Successful! Executable is in the 'dist' folder."
    echo "--------------------------------------------------"
else
    EXIT_CODE=$?
    echo "--------------------------------------------------"
    echo "Error: Build failed."
    echo "--------------------------------------------------"
    exit $EXIT_CODE
fi
