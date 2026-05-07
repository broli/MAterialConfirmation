# 🔑 PKB ERP Command Center - Admin Guide (v3.1)

This guide is intended for administrators who manage the AI infrastructure, database catalog, and system settings.

---

## 🛡️ Enabling Admin Mode
To enable administrative features (Ollama control, Database Management, GitHub Sync):
1. Open `settings.json` in the application folder.
2. Find the `"role"` key and change it from `"user"` to `"admin"`.
3. Save the file and restart the application.

---

## 🧠 Ollama & AI Management
The system uses **Ollama** for complex PDF extraction and batch importing.
- **Start Service:** In the **Settings** menu, use the **▶️ Start Service** button if Ollama is offline.
- **Model Selection:** We recommend using `llama3.1`. Ensure the model is "pulled" in Ollama before use.
- **Show Terminal:** You can toggle this in Settings to see the background AI logs.

---

## 🗄️ Database Management
Admins have access to the **⚙️ Manage Database** button.
- **Edit/Add Products:** Modify the local catalog directly.
- **Batch Add (PDF):** Use this to import multiple items from a PDF catalog. This process is AI-intensive and requires Ollama.
- **Publish Database:** Use this to sync your local changes to the central GitHub repository.

---

## ☁️ GitHub Synchronization & Setup
The application uses GitHub to keep the database synced across the company. 
- **Standard Users:** Download updates directly via the GitHub API (No Git installation required).
- **Admins:** Publish updates using native Git commands (Git installation required).

### Step 1: Install Git (Admins Only)
To publish changes to the database, the Admin machine must have Git installed.
1. Download and install Git from [git-scm.com](https://git-scm.com/downloads).
2. Use the default installation settings.

### Step 2: Create the Repository
1. Go to your GitHub organization/account (e.g., `BathPC`).
2. Create a new **Private** repository named `material-confirmation-db`.
3. Do not initialize it with a README or .gitignore; leave it completely empty.

### Step 3: Create GitHub Tokens
The application requires a Personal Access Token (PAT) in `settings.json`. You should use different tokens depending on the role:

#### For Standard Users (Read-Only Bot)
Users only need to download the database. For security, create a Fine-Grained PAT:
1. Go to **Settings -> Developer Settings -> Personal access tokens -> Fine-grained tokens**.
2. Click **Generate new token**.
3. **Name:** `PKB-DB-ReadOnly-Bot`
4. **Repository access:** `Only select repositories` -> choose `material-confirmation-db`.
5. **Permissions:** `Contents: Read-only` (and `Metadata: Read-only`).
6. Distribute this token in the `settings.json` deployed to standard users.

#### For Admins (Publishing)
Admins need full write access to securely push database updates. Because organizations often restrict fine-grained tokens for third-party git pushes, use a Classic PAT:
1. Go to **Settings -> Developer Settings -> Personal access tokens -> Tokens (classic)**.
2. Click **Generate new token (classic)**.
3. **Name:** `PKB-DB-Admin-Publish`
4. **Scopes:** Check the **`repo`** box (Full control of private repositories).
5. Place this token in your Admin `settings.json`.

---

## 🛠️ Admin Troubleshooting
- **"AI Extraction Error":** Ensure Ollama is running and the `llama3.1` model is available locally.
- **"GitHub Sync Failure":** Check the detailed error message in the Sync Dialog. Ensure your token hasn't expired and you have write access to the `BathPC` organization.
- **"Git Repository is empty":** The first publish will automatically initialize the repository.

*For technical support, contact the System Architect: Carlos.*
