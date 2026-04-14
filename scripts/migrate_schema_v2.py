import os
import yaml

def migrate_file(filepath):
    print(f"Migrating {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        
    if not data:
        return
        
    new_data = []
    for item in data:
        # Create the new item structure
        new_item = {
            'id': item.get('id', 'MISSING_ID'),
            'sku': item.get('sku', item.get('id', '')),  # Fallback to ID if no SKU
            'brand': item.get('brand', 'MISSING_BRAND'),
            'provider': item.get('provider', 'MISSING_PROVIDER'),
            'routing_tag': item.get('routing_tag', 'MISSING_ROUTING'),
        }
        
        # Determine the oneclick_description.
        # Fallback to the old logic if it's missing so they don't lose data tracking.
        old_oneclick = item.get('oneclick_description', "")
        if not old_oneclick:
            old_oneclick = f"{item.get('brand', '')} {item.get('model', '')} {item.get('type', '')} {item.get('finish', '')}".strip()
            if not old_oneclick:
               old_oneclick = "TBD_UPDATE_ME"
               
        new_item['oneclick_description'] = old_oneclick
        
        # Determine if it should be printable based on if it had an image or if it was explicitly hidden
        is_client_facing = item.get('client_facing', True)
        image_file = item.get('image_file', '')
        
        if is_client_facing and image_file:
            # Build description from model/description if any
            desc = item.get('description', '')
            if not desc:
                # Use model as a fallback description
                desc = item.get('model', '')
                
            new_item['printable'] = {
                'finish': item.get('finish', ''),
                'description': desc,
                'dimensions': item.get('dimensions', {}),
                'image_file': image_file
            }
            
        new_data.append(new_item)

    # Write back to file
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(new_data, f, sort_keys=False, default_flow_style=False, allow_unicode=True)
    print(f"Successfully migrated {filepath}")

def main():
    # Find all yaml files in database/categories/
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    categories_dir = os.path.join(base_dir, 'database', 'categories')
    
    if not os.path.exists(categories_dir):
        print(f"Error: Could not find categories directory at {categories_dir}")
        return
        
    for filename in os.listdir(categories_dir):
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            filepath = os.path.join(categories_dir, filename)
            migrate_file(filepath)

if __name__ == "__main__":
    main()
