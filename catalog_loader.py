import yaml
import os
import sys

class CatalogLoader:
    def __init__(self, base_path="database"):
        self.base_path = base_path
        self.categories_path = os.path.join(base_path, "categories")
        self.assets_path = os.path.join(base_path, "assets")
        self.master_catalog = {}
        self.errors = []

    def validate_structure(self):
        """Checks if the required folders exist."""
        for path in [self.categories_path, self.assets_path]:
            if not os.path.exists(path):
                self.errors.append(f"CRITICAL: Folder not found: {path}")
                return False
        return True

    def load_all_categories(self):
        """Reads every .yaml file in the categories folder and validates entries."""
        # FIX: Wipe the internal memory so old edits don't persist as "ghost" items
        self.master_catalog.clear()
        self.errors.clear()

        if not self.validate_structure():
            return None

        files = [f for f in os.listdir(self.categories_path) if f.endswith('.yaml')]
        
        if not files:
            self.errors.append("WARNING: No .yaml files found in categories folder.")
            return {}

        for filename in files:
            file_path = os.path.join(self.categories_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if not data:
                        continue
                    
                    for item in data:
                        self._validate_item(item, filename)
                        # Tag the item with its category for the GUI to use
                        item['category_file'] = filename.replace('.yaml', '') 
                        # Use ID as the key for fast lookup later
                        self.master_catalog[item['id']] = item
            except Exception as e:
                self.errors.append(f"ERROR reading {filename}: {e}")

        return self.master_catalog

    def _validate_item(self, item, filename):
        """Internal check for required fields and image existence."""
        required_fields = ['id', 'sku', 'brand', 'provider', 'routing_tag', 'oneclick_description']
        
        # 1. Check required fields
        for field in required_fields:
            if field not in item:
                self.errors.append(f"MISSING FIELD [{field}] in {filename} (ID: {item.get('id', 'Unknown')})")

        # 2. Check if image exists in assets (if it is a printable item)
        if 'printable' in item and 'image_file' in item['printable']:
            img_path = os.path.join(self.assets_path, item['printable']['image_file'])
            if not os.path.exists(img_path):
                self.errors.append(f"MISSING IMAGE: '{item['printable']['image_file']}' referenced in {filename} (ID: {item.get('id', 'Unknown')})")

    def report(self):
        """Prints a summary of the validation."""
        if not self.errors:
            print(f"✅ Success! Loaded {len(self.master_catalog)} products with no errors.")
        else:
            print(f"⚠️ Found {len(self.errors)} issues during loading:")
            for err in self.errors:
                print(f"  - {err}")

# --- Test Execution ---
if __name__ == "__main__":
    loader = CatalogLoader()
    print("--- Starting PKB Catalog Validation ---")
    catalog = loader.load_all_categories()
    loader.report()
    
    if catalog:
        first_id = list(catalog.keys())[0]
        print(f"\nSample Product (ID: {first_id}):")
        print(f"Brand: {catalog[first_id].get('brand')} | SKU: {catalog[first_id].get('sku')}")