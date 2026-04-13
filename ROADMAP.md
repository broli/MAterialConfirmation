# 🛠️ Development Roadmap: PKB Material Confirmation & ERP System
**Project Owner:** Carlos (Project Manager)  
**Company:** PKB (Payless Kitchen & Bath)

---

## 🎯 Project Objective
Evolution from a standalone material confirmation tool to a **lightweight, robust ERP**. The system will automate the transition from contract data to operational reality, generating tailored outputs for Purchasing, Clients, and Warehouse teams.

---

## 📅 Phase 1: Data Architecture & Catalog
- [x] **Catalog Structure:** Define `catalog.yaml` to store master product data (ID, Name, Specs, Photos).
- [x] **Validation Script:** Create a Python loader to verify that all image paths in the catalog exist on disk.
- [x] **Client Selection Logic:** Implement a system to read a `client_selection.yaml` and map selected IDs to the Master Catalog.

## 📅 Phase 2: PDF Generation Engine (`fpdf2` + `Pillow`)
- [x] **Branding:** Implement PKB headers and marketing footers on every page.
- [x] **Image Optimization:** Use `Pillow` to auto-resize and compress photos for high-quality, low-weight PDFs.
- [x] **Dynamic Layout:** Create a logic to handle "missing photo" placeholders and auto-align product descriptions.

## 📅 Phase 3: Visual Interface (GUI)
- [x] **Modern UI:** Build a desktop app using `CustomTkinter` (Windows 11 / macOS look).
- [x] **Visual Picker:** Allow users to browse the catalog and select products via thumbnails.
- [x] **Data Entry:** Simple forms for Client Name, Project Date, and Bathroom Type (Master, Guest, etc.).
- [x] **One-Click Export:** A button to generate the YAML and the PDF simultaneously.

## 📅 Phase 4: Database Management & Distribution
- [x] **Basic Admin Panel:** Form to save and append new items to YAML with image copying.
- [x] **Advanced Admin UI (Database Browser):** 
    - [x] Read all existing YAML files.
    - [x] Display a Tree/List view showing current items categorized by file.
- [x] **Smart Data Entry Form:**
    - [x] "Add New Product" button that transitions the view from the Database Browser to the Entry Form.
    - [x] Dynamic Dropdowns (`Combobox`) for Category, Brand, Type, and Finish. 

## 📅 Phase 5: Initial Release & Polish
- [x] **Custom "One-Off" Pages:** Allow users to upload a custom image directly into the Document Generator.
- [x] **Grab bar size on selector:** distinguish items that only differ in size.
- [x] **Collapse categories:** dynamic category management in the selector.
- [x] **Add title to extra image:** add a text box before the image for the "one off". (Completed in v2.0)
- [x] **Shared Storage:** Configure the app to read the `database/` folder from a shared PKB OneDrive path. (Completed in v2.0)
- [x] **Packaging (v2.0):** Bundle the app into a standalone `.exe` with version 2.0 branding. (Completed)

---

## 📅 Phase 6: Road to Lightweight ERP (v2.0 Complete) ✅
- [x] **Module Renaming & Refactoring:**
    - [x] Transition to `main.py` entry point and decoupled GUI from legacy PDF engine.
    - [x] Expand database schema (`client_facing`, `routing_tag`, `provider`, `sku`, `printable`).
- [x] **Session & Ingestion Management:**
    - [x] Build Session Persistence (load/save `session_data.json` relative to job directory).
    - [x] Parse "OneClick" PDF Contracts/Estimates to extract Client Name, PO, and items.
- [x] **ERP Verification Center:**
    - [x] Build real-time RapidFuzz matching GUI with confidence traffic lights.
    - [x] Item detail inspector (compare raw PDF vs DB side-by-side).
    - [x] Integrated Catalog Manager for on-the-fly database edits.
- [x] **Modular Output Routing:**
    - [x] **Client PDF:** Grouped by Room (Bath 1, Kitchen, etc.) and filtered by `client_facing` rules.
    - [x] **Excel Injection:** Multi-tab output (one tab per room) into the V7 Material Cart template.
    - [x] **Job-Specific Debugging:** Auto-routing logs and outputs into `Debug/` and `ERP_Automated_Output/` within the job folder.

---
## 📅 Phase 7: refining🔮
- [ ] **Database upgrade:** improve database structure.
- [ ] **line item to database item improvements:** reach 100% accuracy in matching line items to database items.
- [ ] **test PDF material generator:** i believe the pdf output is broken. 
- [ ] **test Excel injection:** i know the excel injection is broken. 

---

## 📅 Phase 8: Advanced Automation & Connectivity (Upcoming) 🔮
- [ ] **Payment schedule email text generator:** Automated text for BT invoices.
- [ ] **TBD** 


---

## 💻 Tech Stack
* **Language:** Python 3.14+
* **Environment:** Virtual Environment (`venv`)
* **Editor:** VS Code 
* **Key Libraries:** `PyYAML`, `fpdf2`, `Pillow`, `CustomTkinter`