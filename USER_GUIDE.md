# 📘 PKB ERP Command Center - User Guide (v3.1)

Welcome to the **PKB Material Confirmation System**. This guide explains the core workflow for processing contracts.

---

## 🚀 Standard Workflow

### 1. Starting the Application
- Open `PKB Material Confirmation System.exe`.
- The system will load your local database automatically.

### 2. Loading a Contract
- Click **📁 Pick Agreement** and select the client's PDF contract.
- The system will automatically read the PDF and match the items against your local database using high-speed fuzzy matching.

### 3. Verifying & Confirming
- **Left Panel:** Shows the raw text extracted from the PDF.
- **Right Panel:** Shows the suggested match from your database.
- **Traffic Lights:** 
    - 🟢 **Green:** High confidence match.
    - 🟡 **Yellow:** Uncertain match (Check the details!).
    - 🔴 **Red:** No match found.
- **Confirming:** Click the **Confirm** button once you are happy with the match.
- **Inspecting:** Click any row to see a side-by-side comparison of the contract text vs. the database entry (including photos).

### 4. Generating Outputs
Once all items are confirmed:
- **📄 Generate Client PDF:** Creates a professional, branded document for the client to sign.
- **📊 Generate Material Cart:** Injects the structured data into your Excel template for the procurement team.

---

## 🛠️ Troubleshooting
- **"Excel Template Missing":** Ensure your `database/templates/` folder contains the required `.xlsx` file.
- **"Image not found":** Ensure the product's `image_file` name in the database matches the filename in `database/assets/`.

*For further assistance, contact the Project Manager: Carlos.*
