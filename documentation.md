# Python Workspace Setup Documentation

This document serves as a template and guide for creating new Python project workspaces. Following these steps ensures your local IDE (e.g., VS Code) and AI assistants can immediately and reliably interact with your project without dependency or environment resolution issues.

## 1. Virtual Environment Initialization

Always create a local virtual environment named `.venv` in the root directory of your new project. This isolates your project dependencies and avoids polluting the global Python installation.

Open your terminal in the new project folder and run:
```powershell
python -m venv .venv
```

## 2. IDE and AI Configuration (`.vscode/settings.json`)

To ensure that tools automatically activate the virtual environment and the Python language server successfully resolves your packages (like `PySide6`), you must configure the workspace settings.

Create a `.vscode` directory in your project root, and inside it, create a `settings.json` file with the following content:

```json
{
    "python.defaultInterpreterPath": ".venv/Scripts/python.exe",
    "python.terminal.activateEnvironment": true,
    "python.terminal.useEnvFile": true,
    "terminal.integrated.profiles.windows": {
        "AutoVenv PowerShell": {
            "source": "PowerShell",
            "args": [
                "-NoExit",
                "-Command",
                "if (Test-Path '.\\.venv\\Scripts\\Activate.ps1') { .\\.venv\\Scripts\\Activate.ps1 }"
            ]
        }
    },
    "terminal.integrated.defaultProfile.windows": "AutoVenv PowerShell"
}
```

### Why is this necessary?
- **`python.defaultInterpreterPath`**: Tells the IDE to use your local `.venv`.
- **`AutoVenv PowerShell`**: Creates a custom terminal profile that automatically executes `Activate.ps1` when a new terminal is launched. This guarantees the AI assistant's integrated terminal runs within the context of your virtual environment.

*Note: If you still experience issues with the language server not finding packages, you may optionally add `python.analysis.extraPaths`: `[".venv/Lib/site-packages"]` to your settings.*

## 3. Package Management

Create a `requirements.txt` file to track dependencies. 
Once your environment is active, install them via:
```powershell
pip install -r requirements.txt
```

## 4. Git Configuration

Ensure your `.gitignore` is set up properly before committing so that environment files, compiled cache, and local secrets aren't published.

**Essential `.gitignore` entries:**
```text
.venv/
__pycache__/
*.pyc
.env
.vscode/
```

## Summary Checklist for New Projects:
- [ ] Create folder
- [ ] Run `python -m venv .venv`
- [ ] Create `.vscode/settings.json` with the custom PowerShell profile
- [ ] Create `.gitignore`
- [ ] `pip install` required libraries and freeze to `requirements.txt`
