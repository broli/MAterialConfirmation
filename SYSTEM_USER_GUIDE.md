# 📘 PKB ERP Command Center - User Guide (v2.6)

Welcome to the **PKB Material Confirmation System**. This guide explains the core workflow for processing contracts and managing your material catalog.

---

## 🚀 Standard Workflow

### 1. Starting the Application
- Open `PKB Material Confirmation System.exe`.
- On startup, the system will check if **Ollama** (your AI engine) is running.
- If it's offline, you'll see a warning in the status bar at the bottom.

### 2. Configuring Settings (First Time Only)
- Click the **⚙️ Settings** button in the top-right corner.
- **Model Selection:** Ensure you have a model selected (we recommend `llama3.1`).
- **Ollama Control:** If Ollama isn't running, click **▶️ Start Service**. You can toggle "Show terminal" if you want to see the background process.
- **PDF Branding:** You can pick a custom cover image here for your generated PDFs.

### 3. Loading a Contract
- Click **📁 Pick Agreement** and select the client's PDF contract.
- The system will automatically:
    1. Read the PDF content.
    2. Use AI to extract the line items.
    3. Match those items against your local database.

### 4. Verifying & Confirming
- **Left Panel:** Shows the raw text extracted from the PDF.
- **Right Panel:** Shows the suggested match from your database.
- **Traffic Lights:** 
    - 🟢 **Green:** High confidence match.
    - 🟡 **Yellow:** Uncertain match (Check the details!).
    - 🔴 **Red:** No match found.
- **Confirming:** Click the **Confirm** button once you are happy with the match.
- **Inspecting:** Click any row to see a side-by-side comparison of the contract text vs. the database entry (including photos).

### 5. Generating Outputs
Once all items are confirmed:
- **📄 Generate Client PDF:** Creates a professional, branded document for the client to sign.
- **📊 Generate Material Cart:** Injects the structured data into your Excel template for the procurement team.

---

## 🗄️ Database Management
Click **⚙️ Manage Database** to browse, edit, or add new products to your catalog.
- **Batch Add (PDF):** Use this to quickly import multiple items from a PDF catalog into your database. The AI will help fill out the forms for you!

---

## 🛠️ Troubleshooting
- **"AI Extraction Error":** Ensure Ollama is running and you have pulled the model specified in Settings.
- **"Excel Template Missing":** Ensure your `database/templates/` folder contains the required `.xlsx` file.
- **"Image not found":** Ensure the product's `image_file` name in the database matches the filename in `database/assets/`.

*For further assistance, contact the Project Manager: Carlos.*
