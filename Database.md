# 🗄️ PKB Database Structure (Payless Kitchen & Bath)

## 📁 System Architecture
The database is designed for **portability** and **concurrency**. Instead of one giant file, products are grouped by category to prevent file corruption and facilitate OneDrive syncing.

```text
PKB_System/
├── database/
│   ├── categories/            # YAML files grouped by type
│   │   ├── faucets.yaml
│   │   ├── toilets.yaml
│   │   └── vanities.yaml
│   └── assets/                # All product images (.jpg, .png)
│
├── sessions/                  # Active client draft selections
│   └── smith_master_bath.yaml 
│
└── output/                    # Generated Confirmation PDFs