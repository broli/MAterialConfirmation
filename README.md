# 🛠️ PKB Material Confirmation & Management System (v2.0)
**From Simple PDF Generation to a Lightweight ERP Ecosystem**

![Version](https://img.shields.io/badge/version-2.0-blue?style=for-the-badge)
![Status](https://img.shields.io/badge/status-Phase%202-orange?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.14%2B-green?style=for-the-badge)

---

## 🌟 Overview
The **PKB Material Confirmation System** is a bespoke operational tool designed for **Payless Kitchen & Bath (PKB)**. What began as a streamlined solution for material verification has evolved into a strategic bridge between sales, project management, and logistics.

Our mission is to eliminate manual errors and repetitive administrative tasks, ensuring that every measurement, color selection, and product specification is perfectly aligned between the client's vision and the project's execution.

---

## 📈 The Evolution: From Phase 1 to Phase 2

### Phase 1: The Foundation (Completed) ✅
In its initial form, the application focused on solving the "Communication Gap" between sales and clients. 
* **Elegant PDF Generation:** Creating professional, branded documentation with high-quality imagery for client approval.
* **Master Catalog:** A unified database of products (Faucets, Vanities, etc.) with consistent specs.
* **Visual Verification:** Ensuring clients see exactly what they are approving before the 3D design and construction phases begin.

### Phase 2: The Lightweight ERP (In Progress) 🚀
We are now transforming this tool into a **Modular ERP System**. Instead of just generating a document, we are building a data-driven engine that powers the entire material lifecycle.
* **Contract Intelligence:** Extracting vital project data from contracts (with human-in-the-loop approval) to populate the system.
* **Workstream Automation:** Transforming a single data entry into multiple tailored outputs.

---

## 🧩 Modular Output System
The core of Version 2.0 is the **Modular Output Engine**, which generates specific documentation for every stakeholder in the process:

| Output Type | Purpose | Key Content |
| :--- | :--- | :--- |
| **🛒 Purchasing List** | Procurement | Model numbers, vendor info, and pricing for the buying team. |
| **🤝 Client Approval** | Client Sign-off | High-res photos, finishes, and dimensions for final signature. |
| **📦 Warehouse Dispatch** | Logistics | Packing lists and pick-lists for the warehouse to prepare for delivery. |
| **📋 PM Task Board** | Management | Automated extraction of repetitive PM tasks directly from contract data. |

---

## 🛠️ Tech Stack
* **GUI:** [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) (Modern, high-DPI Windows 11 aesthetics)
* **Engine:** Python 3.14+
* **Data:** PyYAML (Human-readable, git-friendly database)
* **PDF Core:** fpdf2 & Pillow (Image optimization and precise layout management)
* **Packaging:** PyInstaller (Standalone `.exe` distribution)

---

## 🚀 Getting Started

### Prerequisites
* Python 3.14+
* OneDrive/SharePoint access for the Shared Master Database.

### Installation
1. Clone the repository.
2. Initialize the virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Run the application:
   ```powershell
   python gui_main.py
   ```

---

## 🔭 Future Vision
The road ahead involves deep integration with existing PM workflows. We aim to leverage AI and structured data parsing to strip away the "repetitive noise" of project management, allowing our team to focus on what matters most: **delivering beautiful kitchens and baths.**

---

**Developed for PKB (Payless Kitchen & Bath)**  
*Project Manager: Carlos*
