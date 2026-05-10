#!/bin/bash

# PKB Material Confirmation System - macOS "One-Click" Build Script (v4.0)
# This script automates: Clone -> Environment Setup -> Build -> Cleanup
# Requirement: macOS with Python 3 installed.

REPO_URL="https://github.com/broli/MAterialConfirmation.git"
TEMP_DIR="PKB_Source_Temp"
FINAL_APP_NAME="PKB Material Confirmation System.app"

echo "=================================================="
echo "   PKB ERP Command Center - macOS Builder"
echo "=================================================="

# 1. Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install it from python.org or via Homebrew."
    exit 1
fi

# 2. Check for Git
if ! command -v git &> /dev/null; then
    echo "❌ Git is not found. Installing Xcode Command Line Tools usually fixes this."
    echo "Try running: xcode-select --install"
    exit 1
fi

# 3. Create a clean workspace
echo "📂 Creating temporary workspace..."
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR" || exit

# 4. Clone the repository
echo "🔗 Syncing repository from GitHub..."
git clone "$REPO_URL" .

# 5. Setup Virtual Environment
echo "🐍 Setting up virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# 6. Install dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 7. Patch the .spec file for macOS BUNDLE
# The Windows spec lacks the BUNDLE() call required for macOS .app generation
echo "🛠️ Patching spec file for macOS Bundle..."
if ! grep -q "BUNDLE(" gui_main.spec; then
    cat <<EOF >> gui_main.spec

app = BUNDLE(
    exe,
    name='$FINAL_APP_NAME',
    icon=None,
    bundle_identifier='com.pkb.erp.commandcenter',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'LSBackgroundOnly': 'False',
    },
)
EOF
fi

# 8. Run PyInstaller
echo "🚀 Running PyInstaller..."
python3 -m PyInstaller gui_main.spec --noconfirm

# 9. Move App and Cleanup
echo "🧹 Finalizing and cleaning up..."
if [ -d "dist/$FINAL_APP_NAME" ]; then
    cp -R "dist/$FINAL_APP_NAME" ../
    cd ..
    rm -rf "$TEMP_DIR"
    echo "=================================================="
    echo "✅ BUILD SUCCESSFUL!"
    echo "Application found in: $(pwd)/$FINAL_APP_NAME"
    echo "=================================================="
else
    echo "❌ Error: Build failed. Check the output above."
    cd ..
    exit 1
fi
