# 🔑 PKB ERP Command Center - Admin Guide (v4.0)

This guide is intended for administrators who manage the AI infrastructure, database catalog, and system settings.

---

## 🛡️ Enabling Admin Mode
To enable administrative features (AI controls, Database Management, GitHub Sync):
1. Locate `settings.json` in the application folder. 
   - **Note:** This file is automatically created **after the first run** (once you select your team).
2. Open `settings.json`, find the `"role"` key, and change it from `"user"` to `"admin"`.
3. Save the file and restart the application.

---

## 🧠 AI Infrastructure (Hybrid Approach)
The system uses a prioritized hybrid AI model to ensure maximum reliability and speed.

### 🌌 Stage 1: Google Gemini (Primary)
The system prioritizes **Gemini 1.5** for all matching and ingestion tasks.

#### 🔑 Getting an API Key
To use Gemini, you need a Google AI API Key:
1. Go to the [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account and click **"Get API key"**.
3. **Free vs. Paid:**
   - **Free Tier:** The application works perfectly with a free API key. However, you will encounter strict rate limits and a daily quota. The system will automatically pause and wait when these are hit.
   - **Paid Tier:** If you require faster processing for large catalogs without pauses, consider enabling billing in your Google Cloud project to increase your RPM (Requests Per Minute).

#### ⚙️ How it Works
- **API Key Required:** You must provide your key in the **Settings** menu (visible in Admin mode) to enable Gemini.
- **Dynamic Ranking:** The system automatically pulls the latest models available for your key and ranks them from **best to worst** (e.g., prioritized 3.1 Pro -> 3.0 Flash -> 1.5 Flash).
- **Waterfall Failover:** If a model hits a 429 rate limit or quota exhaustion, the system "falls back" to the next model in the ranked list.
- **Automatic Dropping:** Once a model is confirmed exhausted, it is permanently removed from the session's active pool to prevent looping.

### 🦙 Stage 2: Ollama (Local Fallback)
If no Gemini API key is provided, or for specific local extraction tasks, the system falls back to **Ollama**.
- **Local Power:** Since Ollama runs on your hardware, it works offline but is slower than Gemini for bulk tasks.
- **Start Service:** Use the **▶️ Start Service** button in Settings if Ollama is offline.
- **Model:** Default is `llama3.1`. Ensure the model is "pulled" via the terminal (`ollama pull llama3.1`) before use.

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
