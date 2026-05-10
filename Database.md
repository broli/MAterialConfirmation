# 🗄️ PKB Database & Schema (v4.0)

This document defines the architecture and data structure for the **Payless Kitchen & Bath (PKB)** material confirmation system.

---

## 📁 System Architecture
The database is designed for **portability** and **concurrency**. Instead of one giant file, products are grouped by category to prevent file corruption and facilitate cloud syncing.

### 🏘️ Dual-Database Structure
The system maintains two distinct database roots:

1.  **`/database/` (Production):** The "Source of Truth." This catalog is synced across the entire company via GitHub. Only **Administrators** can publish updates here.
2.  **`/staging_database/` (Review Queue):** All AI-extracted items from the bulk ingestion pipeline are placed here first. Items remain in "Staging" until an Admin reviews and approves them, moving them into the Production catalog.

### 📂 Folder Hierarchy
```text
PKB_System/
├── database/ / staging_database/
│   ├── categories/            # YAML files grouped by type (e.g., Faucets.yaml)
│   └── assets/                # All product images (.jpg, .png)
├── sessions/                  # Active client selections (Job Folders)
└── output/                    # Generated Confirmation PDFs
```

### 🛡️ Filename Sanitization
To prevent filesystem errors, category filenames are automatically sanitized:
- Special characters (like `&`, `/`, `\`) are replaced with underscores `_`.
- *Example:* "Painting / Patch" -> `Painting_Patch.yaml`.
- All files must use the `.yaml` extension.

---

## 📑 Product Schema Definition

### 📐 General Rules
1. **Encoding:** Use `UTF-8` for all YAML files.
2. **Imperial Units:** All measurements must be in **Inches**.
3. **Escaping Inches:** Wrap values containing double quotes in single quotes.
   - *Correct:* `width: '30"'`
   - *Incorrect:* `width: 30"`

### 🏗️ Data Model
| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `id` | String | Yes | Unique PKB Identifier (e.g., `PKB-VAN-48-GRY`). |
| `sku` | String | Yes | Manufacturer or Vendor part number. |
| `brand` | String | Yes | Manufacturer name. |
| `routing_tag` | String | Yes | Export logic: `IGNORE`, `WAREHOUSE`, `PROCURE`, or `WH_OR_PROCURE`. |
| `oneclick_description` | String | Yes | The target string used for fuzzy matching. |
| `aliases` | List[String] | No | Known alternative descriptions or typo variations to ensure perfect future matches. |
| `printable` | Object | No | Determines if the item appears on the Client PDF. |

### The `printable` Object
If an item should appear on the Client PDF, it must include this dictionary:
| Field | Type | Description |
| :--- | :--- | :--- |
| `finish` | String | Color/Texture (e.g., Matte Black). Used for filtering. |
| `description` | String | Marketing text shown to the client. |
| `dimensions` | Dictionary | Flexible keys (width, height, depth, etc.). |
| `image_file` | String | Filename in the `/assets/` folder. |

---

## 💡 Dimension Flexibility (Example)

The `dimensions` field is dynamic. Only include the keys relevant to the specific product type.

### Vanity Example
```yaml
- id: PKB-VAN-48-GRY
  sku: VAN-48-GRY-WYN
  brand: "Wyndham"
  routing_tag: "WAREHOUSE"
  oneclick_description: "Wyndham Icon 48 inch Freestanding Vanity Dark Gray"
  printable:
    finish: "Dark Gray"
    description: "Modern vanity with integrated porcelain sink."
    dimensions: 
      width: '48"'
      height: '34"'
      depth: '22"'
    image_file: "wyndham_icon_48.jpg"
```

🛠️ **Validation Checklist:**
- [ ] Is the `id` unique across the entire database?
- [ ] Does the `image_file` name match the file in `/assets/` exactly?
- [ ] Are all inch marks (`"`) wrapped in single quotes?
- [ ] Is the category name correctly sanitized for the filename?