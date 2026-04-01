# 🛠️ Development Roadmap: Bathroom Materials Confirmation System
**Project Owner:** Carlos (Project Manager)  
**Company:** PKB (Payless Kitchen & Bath)

---

## 🎯 Project Objective
Automate the generation of professional PDF documents for client material confirmation. This ensures all specs (measurements, colors, and photos) are approved by the client before moving to the 3D Design stage.

---

## 📅 Phase 1: Data Architecture & Catalog (Current)
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
- [ ] **Advanced Admin UI (Database Browser):** - Read all existing YAML files.
    - Display a Tree/List view showing current items categorized by file (e.g., Faucets -> Kohler Purist).
- [ ] **Smart Data Entry Form:**
    - "Add New Product" button that transitions the view from the Database Browser to the Entry Form.
    - Dynamic Dropdowns (`Combobox`) for Category, Brand, Type, and Finish. These will auto-populate by reading existing database entries, but allow the user to type in a new value if needed.
- [ ] **Shared Storage:** Configure the app to sync the catalog and assets via OneDrive for the whole team.
- [ ] **Packaging:** Bundle the app into an `.exe` (Windows) using `PyInstaller`.

---

## 💻 Tech Stack
* **Language:** Python 3.14+
* **Environment:** Virtual Environment (`venv`)
* **Editor:** VS Code (Vim mode)
* **Key Libraries:** `PyYAML`, `fpdf2`, `Pillow`, `CustomTkinter`