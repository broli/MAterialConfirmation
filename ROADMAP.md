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

## 📅 Phase 6: Road to Lightweight ERP (Current Evolution) 🚀
- [ ] **Contract Data Engine:**
    - [ ] Implement a system to read contract info (PDF/JSON/YAML).
    - [ ] Create a "Review & Approve" UI for PMs to verify extracted contract data before processing.
- [ ] **Modular Output System:**
    - [ ] **Purchasing Logic:** Generate a "To Buy" list with model numbers and procurement specs.
    - [ ] **Client Approval:** Enhanced material confirmation documents with signed placeholders.
    - [ ] **Warehouse Dispatch:** Generate packing lists and pick-lists for logistics coordination.
- [ ] **PM Workflow Automation:**
    - [ ] Identification and extraction of repetitive tasks mentioned in contracts.
    - [ ] Automated logging of project milestones based on material selection cycles.

---

## 💻 Tech Stack
* **Language:** Python 3.14+
* **Environment:** Virtual Environment (`venv`)
* **Editor:** VS Code 
* **Key Libraries:** `PyYAML`, `fpdf2`, `Pillow`, `CustomTkinter`