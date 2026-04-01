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
| `id` | String | Yes | Unique SKU or Identifier. Used to link selections. |
| `brand` | String | Yes | Manufacturer (e.g., Kohler, Delta, Moen). |
| `model` | String | Yes | The specific product line (e.g., Purist, Trinsic). |
| `type` | String | Yes | Sub-category (e.g., Widespread Faucet, Alcove Tub). |
| `finish` | String | Yes | Color or Texture (e.g., Matte Black, Brushed Gold). |
| `dimensions` | Dictionary | No | **Flexible field.** Contains specific measurements. |
| `description` | String | Yes | Marketing text for the client to read. |
| `image_file` | String | Yes | Filename located in the `/assets/` folder. |

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