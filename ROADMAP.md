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
- [x] **Add title to extra image:** add a text box before the image for the "one off". (Completed in v2.6)
- [x] **Shared Storage:** Configure the app to read the `database/` folder from a shared PKB OneDrive path. (Completed in v2.6)
- [x] **Packaging (v2.6):** Bundle the app into a standalone `.exe` with version 2.0 branding. (Completed)

---

## 📅 Phase 6: Road to Lightweight ERP (v2.6 Complete) ✅
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

## 📅 Phase 7: Hybrid LLM Matching Engine (Complete) ✅
- [x] **Contract Item to Database Item Improvements:** Reach 100% accuracy in matching by migrating to a Hybrid LLM + Deterministic approach.
    - [x] Build `llm_service.py` to interface with Local Ollama (using Instructor & Pydantic).
    - [x] Update `MatchingEngine` to parse and obey strictly generated attribute constraints (Finish, Dimensions).
- [x] **Database Manager / Add Item Upgrade:**
    - [x] Remove manual "Add Blank Item" form (move old code to backup).
    - [x] Create "Batch Add from PDF" UI queue to automatically surface unmatched items.
    - [x] Auto-fill the new item form using local LLM inference.
    - [x] Add explicit "Confirm LLM Rules" window before saving a new item to DB.
- [x] **test PDF material generator:** verify the pdf output generator behaviour. (FIXED)
- [x] **test Excel injection:** verify the excel injection functionality. 

---

## 📅 Phase 8: Performance & Advanced Automation (Complete) ✅
- [x] **Pipeline Optimization:** Multi-thread LLM calls during batch PDF parsing to remove UI freezes.
- [x] **Matching Diagnostic Logs:** Add comprehensive debug logging to track LLM extractions, filtered candidate sizes, and RapidFuzz scoring.
- [x] **Database Migration:** Script to clean legacy regex fields (`matching_rules`), normalize providers, and enforce canonical schema ordering across all catalog files.
- [x] **Ollama Orchestration:** Added `SettingsWindow` to manage `ollama serve` lifecycle, pull/delete models, and select active models.
- [x] **Dynamic PDF Branding:** Allow users to pick and import custom cover images via settings.

## 📅 Phase 9: Gemini API & Advanced Database Scaling (Complete) ✅
- [x] **Gemini Integration:** Migrated from purely local Ollama to a high-speed Gemini API backend with Instructor-based schema validation.
- [x] **Intelligent Model Waterfall:** Implemented a ranked failover system that automatically cycles through available Gemini models to handle rate limits without interruption.
- [x] **Robust Quota Management:** Persistent model pool management that drops exhausted models for the session to prevent infinite retry loops.
- [x] **Advanced Batch Editor:** Replaced the legacy single-field editor with the full product GUI in batch mode, featuring "Apply/Enable" checkboxes and auto-selection logic.
- [x] **Deterministic Filename Sanitization:** Regex-based sanitization for categories (e.g., "Painting / Patch" -> "Painting_Patch.yaml") to ensure stable filesystem mapping.

## 📅 Phase 10: ERP Expansion & Workflow (In Progress) 🔮
- [ ] **Inventory Integration:** Basic connection to stock, to auto route requests.
- [ ] **Payment schedule email text generator:** Automated text for BT invoices.
- [ ] **Automatic filling of job material Excel:** For cart reviews for the PM based on the job folder name.
- [x] **Update PDF Generator:** Handle 2 items per page for better document density.
- [ ] **Create database maintenance tool:** Clean up unused items, merge duplicates, etc.
    

## 📅 Phase X: MISC and future ideas, even dreaming
- [ ] **Support full-width items in PDF** fallback for items that need to span both columns.
- [ ] **real usage** get the real usage of features to improve the app.
- [ ] **user feedback** get user feedback to improve the app & add new features.


---

## 💻 Tech Stack
* **Language:** Python 3.14+
* **Environment:** Virtual Environment (`venv`)
* **Editor:** VS Code 
* **Key Libraries:** `PyYAML`, `fpdf2`, `Pillow`, `PySide6`, `qdarktheme`