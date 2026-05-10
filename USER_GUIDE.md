# 📘 PKB ERP Command Center - User Guide (v4.0)

Welcome to the **PKB Material Confirmation System**. This guide explains the core workflow for processing contracts.

---

## 🚀 Standard Workflow

### 1. Starting the Application & Setup
- Open `PKB Material Confirmation System.exe`.
- **First Run Only:** You will be greeted by a "Select Your Team" screen. 
    - Click on your team (e.g., **Kitchen Team** or **Bath Team**).
    - This will automatically configure your database connection and team branding.
- Once configured, the system will load your team's specific database automatically. You won't see the selection screen again.

### 2. Loading a Contract
- Click **📁 Pick Agreement** and select the client's PDF contract.
- The system will automatically read the PDF and match the items against your local database using high-speed fuzzy matching. This happens instantly for standard users.

### 3. Verifying & Confirming
- **Left Panel:** Shows the raw text extracted from the PDF.
- **Right Panel:** Shows the suggested match from your database.
- **Traffic Lights:** 
    - 🟢 **Green:** High confidence match (usually 100% exact).
    - 🟡 **Yellow:** Uncertain match. **Always click to inspect these!**
    - 🔴 **Red:** No match found in the current catalog.
- **Confirming:** Click the **Confirm** button once you are happy with the match.
- **Inspecting:** Double-click any row to see a side-by-side comparison of the contract text vs. the database entry (including photos).

### 4. Generating Outputs
Once all items are confirmed (or manually resolved):
- **📄 Generate Client PDF:** Creates a professional, branded document for the client to sign.
- **📊 Generate Material Cart:** Injects the structured data into your Excel template for the procurement team.

---

## 💡 Pro Tips for Users
- **Partial Matches:** If a match is 🟡 Yellow, the system might have found the right item but a different finish. Check the "Inspecting" view to verify.
- **Catalog Updates:** If you encounter a 🔴 Red light for an item you know is in the catalog, notify an **Administrator**. They can update the database and sync the changes to your machine.
- **Team Switching:** If you accidentally joined the wrong team, contact an Admin to reset your `settings.json` file.

---

## 🛠️ Troubleshooting
- **"Excel Template Missing":** Ensure your `database/templates/` folder contains the required `.xlsx` file.
- **"Image not found":** Ensure the product's `image_file` name in the database matches the filename in `database/assets/`.

*For further assistance, contact the Project Manager: Carlos.*
