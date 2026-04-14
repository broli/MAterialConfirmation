# 📑 PKB Product Schema Definition (YAML)

This document defines the standard structure for all product data used in the **Payless Kitchen & Bath (PKB)** material confirmation system.

## 📐 General Rules
1. **File Format:** All files must use the `.yaml` extension.
2. **Encoding:** Use `UTF-8` to ensure special characters (like the inch symbol) render correctly.
3. **Imperial Units:** All measurements must be in **Inches**. 
4. **Escaping Inches:** Because the double quote (`"`) is a special character in YAML, you must wrap the value in single quotes or use a backslash.
   * *Correct:* `width: '30"'` or `width: "30\""`
   * *Incorrect:* `width: 30"`

---

## 🏗️ The Data Model

### Field Descriptions
| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `id` | String | Yes | Unique internal PKB Identifier. Used to link selections. |
| `sku` | String | Yes | (ERP) Manufacturer or Vendor part number. |
| `brand` | String | Yes | (ERP) Manufacturer (e.g., Kohler). Not shown to client. |
| `provider` | String | Yes | (ERP) Purchasing origin (e.g., "Kohler Direct"). |
| `routing_tag` | String | Yes | (ERP) Used for Excel dispatch ("Warehouse", "Link", etc). |
| `purchase_link` | String | No | URL string or action code ("CRM", "email") for purchasing. |
| `oneclick_description` | String | Yes | **REQUIRED.** The exact target string the Matching Engine expects. |
| `printable` | Object | No | Client-facing data. (If omitted, item is strictly hidden). |

### The `printable` Object
If an item should appear on the Client PDF, it must include a `printable` dictionary:
| Field | Type | Description |
| :--- | :--- | :--- |
| `finish` | String | Color or Texture (e.g., Matte Black, Brushed Gold). |
| `description` | String | Marketing text for the client. Replaces `model`/`brand`. |
| `dimensions` | Dictionary | **Flexible field.** Contains specific measurements. |
| `image_file` | String | Filename located in the `/assets/` folder. |

*(Note: `quantity` is tracked dynamically in the active Job Session, not in this catalog).*

---

## 💡 Dimension Flexibility (Examples)

The `dimensions` field is dynamic. Only include the keys relevant to the specific product type.

### 1. Vanities (3 Dimensions)
Standard case for furniture where Width, Height, and Depth are critical.
```yaml
- id: PKB-VAN-48-GRY
  brand: "Wyndham"
  model: "Icon"
  type: "Freestanding Vanity"
  finish: "Dark Gray"
  dimensions: 
    width: '48"'
    height: '34"'
    depth: '22"'
  description: "Modern vanity with integrated porcelain sink and soft-close drawers."
  image_file: "wyndham_icon_48.jpg"
```

🛠️ Validation Checklist
Before adding a new product:

[ ] Is the id unique?

[ ] Does the image_file name match the file in /assets/ exactly?

[ ] Are all inch marks (") properly escaped in the YAML?

[ ] Is the category file saved in the database/categories/ folder?