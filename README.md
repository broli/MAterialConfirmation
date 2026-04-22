# 🛠️ PKB Material Confirmation & Management System (v2.1)
**From Simple PDF Generation to a Lightweight ERP Ecosystem**

![Version](https://img.shields.io/badge/version-2.1-blue?style=for-the-badge)
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
* **AI-Powered Matching Engine:** A two-step deterministic pipeline using local LLMs to parse raw contract text into structured data, followed by strict attribute-based filtering for 100% accuracy.
* **Contract Intelligence:** Extracting vital project data from contracts (with human-in-the-loop approval) to populate the system.
* **Workstream Automation:** Transforming a single data entry into multiple tailored outputs.

---

## 🧠 The Matching Pipeline
The system uses a sophisticated matching logic to link messy PDF contract strings to our master catalog:

1. **LLM Sanitization Layer:** Uses **Ollama (Llama 3)** and **Instructor** to parse raw text into a validated **Pydantic** model (`ContractItem`).
2. **Deterministic Filter:** Strictly filters the catalog by extracted attributes (Finish, Size, etc.). If an item contradicts these fields, it is discarded.
3. **Fuzzy Fallback:** Applies a final fuzzy string match (RapidFuzz) on the remaining candidates to find the most accurate product link.

---

## 🧩 Modular Output System
The core of the system is the **Modular Output Engine**, which generates specific documentation for every stakeholder in the process:

| Output Type | Purpose | Key Content |
| :--- | :--- | :--- |
| **🛒 Purchasing List** | Procurement | Model numbers, vendor info, and pricing for the buying team. |
| **🤝 Client Approval** | Client Sign-off | High-res photos, finishes, and dimensions for final signature. |
| **📦 Warehouse Dispatch** | Logistics | Packing lists and pick-lists for the warehouse to prepare for delivery. |
| **📋 PM Task Board** | Management | Automated extraction of repetitive PM tasks directly from contract data. |

---

## 🛠️ Tech Stack
* **GUI:** [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) (Modern Windows 11 aesthetics)
* **AI Engine:** [Ollama](https://ollama.com/) (Local Llama 3) + [Instructor](https://github.com/jxnl/instructor) + [Pydantic](https://docs.pydantic.dev/)
* **Matching:** RapidFuzz (String similarity)
* **Data:** PyYAML (Git-friendly database)
* **PDF Core:** fpdf2 & Pillow

---

## 🚀 Getting Started

### Prerequisites
* Python 3.14+
* **Ollama Installed & Running** (Download from [ollama.com](https://ollama.com/))
* **Llama 3 Model Pulled:** Run `ollama run llama3` in your terminal.

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
   python main.py
   ```

---

## 🔭 Future Vision
The road ahead involves deep integration with existing PM workflows. We aim to leverage AI and structured data parsing to strip away the "repetitive noise" of project management, allowing our team to focus on what matters most: **delivering beautiful kitchens and baths.**

---

**Developed for PKB (Payless Kitchen & Bath)**  
*Project Manager: Carlos*
