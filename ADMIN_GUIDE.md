# 🔑 PKB ERP Command Center - Admin Guide (v4.0)

This guide is intended for administrators who manage the AI infrastructure, database catalog, and system settings.

---

## 🛡️ Enabling Admin Mode
To enable administrative features (Ollama control, Database Management, GitHub Sync):
1. Open `settings.json` in the application folder.
2. Find the `"role"` key and change it from `"user"` to `"admin"`.
3. Save the file and restart the application.

---

## 🧠 AI Infrastructure (Gemini & Ollama)
The system uses a hybrid AI approach for PDF extraction and database scaling.

### 🌌 Gemini API (Recommended for Bulk)
The system prioritizes **Google Gemini 1.5** for high-accuracy bulk ingestion.
- **Model Waterfall:** If one Gemini model hits a rate limit (429 error), the system automatically "falls back" to the next available model in the ranking.
- **Quota Management:** Once a model hits its daily quota, it is permanently dropped from the active pool for that session to prevent loops.
- **Configuration:** Ensure your `GEMINI_API_KEY` is set in `settings.json`.

### 🦙 Ollama (Local Fallback)
Used for complex PDF extraction when offline or for specific local tasks.
- **Start Service:** Use the **▶️ Start Service** button in Settings if Ollama is offline.
- **Model:** Recommended `llama3.1`. Ensure the model is "pulled" before use.

---

## 🗄️ Database Management
Admins have access to the **⚙️ Manage Database** toolset.

### 📝 Edit & Approval Workflow
- **Staging Database:** All new AI-extracted items are placed in the `staging_database`. You must review and "Approve" them before they move to the Production catalog.
- **Advanced Batch Edit:** Select multiple rows and click **Batch Edit Selected**. 
  - **Enable/Apply Checkboxes:** Use the checkboxes next to each field to signal which data to overwrite.
  - **Auto-Selection:** The app automatically checks the box as you type.
  - **Explicit Clear:** Check a box and leave the field empty to explicitly wipe that data across the batch.
  
### 📥 Bulk Ingestion Pipeline (PDF)
1. **Stage 1 (Extract):** Parses raw PDF lines into a local processing queue.
2. **Stage 2 (Process):** Uses the Gemini Waterfall to extract structured product data (Brand, SKU, Dimensions, Finish).
3. **Stage 3 (Review):** Items appear in the Database Manager's Staging tab for final verification.

### 🌐 Synchronization
- **Publish Database:** Syncs your local changes to the central GitHub repository.
- **GitHub Sync:** Keeps the entire team's catalog consistent.

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
