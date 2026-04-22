import os
import sys
sys.path.append(os.getcwd())

import yaml
from llm_service import LocalLLMClient

def repair_database():
    categories_dir = "database/categories"
    if not os.path.exists(categories_dir):
        print(f"Directory not found: {categories_dir}")
        return

    # Instantiate the client to access our new procedural compile_matching_rules
    # It won't actually call Ollama because we changed the logic
    llm = LocalLLMClient(model="none")

    total_updated = 0
    
    for filename in os.listdir(categories_dir):
        if not filename.endswith(".yaml"):
            continue
            
        filepath = os.path.join(categories_dir, filename)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            items = yaml.safe_load(f) or []
            
        changed = False
        
        for item in items:
            # We want to re-generate matching_rules for ALL items that are printable
            # (since matching rules rely heavily on dimensions and finish)
            printable = item.get("printable")
            if not printable:
                continue
                
            # Build the product_dict as expected by compile_matching_rules
            product_dict = {
                "category": filename.replace(".yaml", ""),
                "brand": item.get("brand", ""),
                "finish": printable.get("finish", ""),
                "dimensions": printable.get("dimensions", {}),
                "description": printable.get("description", "")
            }
            
            new_rules = llm.compile_matching_rules(product_dict)
            
            # Compare and update
            old_rules = item.get("matching_rules", {})
            if new_rules != old_rules:
                item["matching_rules"] = new_rules
                changed = True
                total_updated += 1
                
        if changed:
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(items, f, sort_keys=False, allow_unicode=True)
            print(f"Updated {filename}")

    print(f"\nDatabase Repair Complete! Total items updated: {total_updated}")

if __name__ == "__main__":
    repair_database()
