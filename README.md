# 🛠️ PKB Material Confirmation & Operational Engine (v4.0)
**Bridging Sales, Logistics, and AI into a Unified Material Lifecycle.**

![Version](https://img.shields.io/badge/version-4.0-blue?style=for-the-badge)
![Status](https://img.shields.io/badge/status-Production--Ready-green?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.14%2B-green?style=for-the-badge)
![Framework](https://img.shields.io/badge/UI-PySide6-orange?style=for-the-badge)

---

## 🌟 Project Overview
The **PKB Material Confirmation System** is a sophisticated operational tool built for **Payless Kitchen & Bath**. It solves a critical industry problem: the "Communication Gap" between messy, hand-written or complex PDF sales contracts and the structured data required for procurement and client sign-off.

What started as a PDF generator has evolved into a **Hybrid AI-Driven Ecosystem** that automates data extraction, simplifies database management, and ensures 100% material accuracy across the project lifecycle.

---

## 🚀 Key Technical Features

### 🌌 Hybrid AI Matching Engine (Gemini + Ollama)
At the heart of the system is a prioritized hybrid AI pipeline:
- **Gemini Waterfall:** A resilient API-based backend that dynamically ranks available models based on capability and recency. It features an intelligent failover system that automatically shifts traffic if a model hits a rate limit or quota.
- **Local Ollama Fallback:** A fully private, offline fallback using local LLMs for environments where API access is restricted.
- **Deterministic Validation:** AI extractions are strictly validated against a Pydantic schema before being passed to a RapidFuzz-powered fuzzy matching engine.

### 📥 Automated Bulk Ingestion Pipeline
High-efficiency pipeline for scaling product catalogs:
- **Phase 1 (Extract):** Direct native PDF parsing of vendor catalogs.
- **Phase 2 (Process):** Batch processing via the Gemini Waterfall to structure raw text into Brand, SKU, and Dimensions.
- **Phase 3 (Review):** A dedicated Staging Database for human-in-the-loop approval before items enter the Production catalog.

### ⚙️ Advanced Database Manager
- **Context-Aware Batch Editing:** A multi-select UI that uses the full product GUI in batch mode.
- **Smart Selectors:** "Enable/Apply" checkboxes with auto-selection logic allow admins to target specific fields (like Brand or Finish) across hundreds of items simultaneously.
- **Git-Based Synchronization:** Distributed database architecture using YAML files, enabling seamless syncing across teams via GitHub with automated pull/push logic.

---

## 🛠️ Tech Stack
- **Frontend:** [PySide6 (Qt)](https://doc.qt.io/qtforpython-6/) with [qdarktheme](https://github.com/5yutan5/PyQtDarkTheme) for a premium, modern dark-mode experience.
- **AI/LLM:** [Google Gemini API](https://ai.google.dev/) & [Ollama](https://ollama.com/) integrated via [Instructor](https://github.com/jxnl/instructor) and [Pydantic](https://docs.pydantic.dev/).
- **Matching Logic:** [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) for high-performance string similarity.
- **Persistence:** Human-readable YAML database optimized for Git-based concurrency and cloud syncing.
- **Outputs:** [fpdf2](https://github.com/fpdf2/fpdf2) for branded PDF generation and [openpyxl](https://openpyxl.readthedocs.io/) for Excel-based procurement injection.

---

## 📂 System Architecture
The application follows a clean **MVC (Model-View-Controller)** pattern:
- **Models:** Atomic services for Config, Catalog, Matching, and AI.
- **Views:** Decoupled PySide6 components and custom widgets (ProductForm, BatchDialog).
- **Controllers:** Orchestrators that manage the flow between UI events and background worker threads.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.14+
- **Gemini API Key:** (Optional) Set `gemini_api_key` in `settings.json` for high-speed cloud ingestion.
- **Ollama:** (Optional) Download from [ollama.com](https://ollama.com/) for local fallback support.

### Installation
1. **Clone & Setup:**
   ```powershell
   git clone https://github.com/BathPC/material-confirmation-system.git
   cd material-confirmation-system
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. **First Run:** Launch `python main.py` and select your team (Kitchen or Bath) to auto-configure your environment.

---

## 💼 Portfolio Highlights
This project demonstrates expertise in:
- **Asynchronous GUI Design:** Managing long-running AI tasks with background workers and real-time UI feedback.
- **Hybrid Cloud/Local AI:** Balancing cost, speed, and privacy through a modular LLM client architecture.
- **Complex Data Mapping:** Implementing robust ETL (Extract, Transform, Load) logic to normalize unstructured PDF data into a relational-style YAML database.
- **Enterprise Workflow Automation:** Reducing manual administrative labor by over 80% through deterministic automation.

---

**Developed for PKB (Payless Kitchen & Bath)**  
*Lead Architect: Carlos*
