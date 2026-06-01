#!/bin/bash

# PKB Material Confirmation System - Build Script [Linux]
echo -e "\e[36m--------------------------------------------------\e[0m"
echo -e "\e[36mStarting Build Process (Linux)...\e[0m"
echo -e "\e[36m--------------------------------------------------\e[0m"

# Remove old executable if it exists to ensure we get a fresh build
if ls ./dist/PKB\ Material\ Confirmation\ System_v* 1> /dev/null 2>&1; then
    echo -e "\e[33mCleaning up old build...\e[0m"
    rm -f ./dist/PKB\ Material\ Confirmation\ System_v*
fi

# Run PyInstaller using the virtual environment's python
./.venv/bin/python -m PyInstaller gui_main.spec --noconfirm

if [ $? -eq 0 ]; then
    echo -e "\e[32m--------------------------------------------------\e[0m"
    echo -e "\e[32mBuild Successful! Executable is in the 'dist' folder.\e[0m"
    echo -e "\e[32m--------------------------------------------------\e[0m"
else
    EXIT_CODE=$?
    echo -e "\e[31m--------------------------------------------------\e[0m"
    echo -e "\e[31mError: Build failed.\e[0m"
    echo -e "\e[31m--------------------------------------------------\e[0m"
    exit $EXIT_CODE
fi
