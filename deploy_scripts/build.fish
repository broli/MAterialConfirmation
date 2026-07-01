#!/usr/bin/env fish

# PKB Material Confirmation System - Build Script [Linux]
set_color cyan
echo "--------------------------------------------------"
echo "Starting Build Process (Linux)..."
echo "--------------------------------------------------"
set_color normal

# Remove old executable if it exists to ensure we get a fresh build
set_color yellow
echo "Cleaning up old build..."
set_color normal
rm -f ./dist/PKB\ Material\ Confirmation\ System_v* 2>/dev/null

# Run PyInstaller using the virtual environment's python
./.venv/bin/python -m PyInstaller gui_main.spec --noconfirm
set EXIT_CODE $status

if test $EXIT_CODE -eq 0
    set_color green
    echo "--------------------------------------------------"
    echo "Build Successful! Executable is in the 'dist' folder."
    echo "--------------------------------------------------"
    set_color normal
else
    set_color red
    echo "--------------------------------------------------"
    echo "Error: Build failed."
    echo "--------------------------------------------------"
    set_color normal
    exit $EXIT_CODE
end
