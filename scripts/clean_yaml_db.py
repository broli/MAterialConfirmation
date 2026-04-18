import os
import yaml

def clean_database(base_path="database"):
    categories_path = os.path.join(base_path, "categories")
    if not os.path.exists(categories_path):
        print(f"Error: {categories_path} not found.")
        return

    allowed_root_keys = {
        'id', 'sku', 'brand', 'provider', 'routing_tag', 
        'purchase_link', 'oneclick_description', 'printable'
    }
    
    allowed_printable_keys = {
        'finish', 'description', 'dimensions', 'image_file'
    }
    
    valid_routing_tags = {'IGNORE', 'WAREHOUSE', 'PROCURE', 'WH_OR_PROCURE'}

    total_files = 0
    total_items = 0
    total_cleaned_items = 0

    for filename in os.listdir(categories_path):
        if not filename.endswith('.yaml'):
            continue
            
        file_path = os.path.join(categories_path, filename)
        total_files += 1
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            if not data:
                continue

            cleaned_data = []
            file_modified = False

            for item in data:
                total_items += 1
                cleaned_item = {}
                item_modified = False
                
                # Order keys logically
                for key in ['id', 'sku', 'brand', 'provider', 'routing_tag', 'purchase_link', 'oneclick_description']:
                    if key in item:
                        cleaned_item[key] = item[key]
                    else:
                        # Ensure fields exist, empty if not required
                        if key == 'id':
                            cleaned_item[key] = item.get('id', 'UNKNOWN_ID')
                        elif key == 'sku':
                            cleaned_item[key] = item.get('sku', 'UNKNOWN_SKU')
                        elif key == 'oneclick_description':
                            cleaned_item[key] = item.get('oneclick_description', 'UNKNOWN_DESC')
                        elif key == 'routing_tag':
                            cleaned_item[key] = 'WAREHOUSE'
                        else:
                            # optional fields
                            pass
                            
                # Fix routing tag
                rt = cleaned_item.get('routing_tag', '').upper()
                if rt not in valid_routing_tags:
                    cleaned_item['routing_tag'] = 'WAREHOUSE'
                    item_modified = True
                else:
                    cleaned_item['routing_tag'] = rt
                    
                # Handle printable
                if 'printable' in item and isinstance(item['printable'], dict):
                    printable_cleaned = {}
                    for k in ['finish', 'description', 'dimensions', 'image_file']:
                        if k in item['printable']:
                            printable_cleaned[k] = item['printable'][k]
                            
                    # Check for dropped keys
                    for k in item['printable']:
                        if k not in allowed_printable_keys:
                            item_modified = True
                            
                    cleaned_item['printable'] = printable_cleaned
                
                # Check for dropped root keys
                for k in item:
                    if k not in allowed_root_keys:
                        item_modified = True
                        
                cleaned_data.append(cleaned_item)
                if item_modified:
                    file_modified = True
                    total_cleaned_items += 1

            # Only write back if we actually cleaned/modified something or if we want to enforce standard formatting
            # Let's write back everything to ensure standard formatting (indentation, ordering)
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(cleaned_data, f, sort_keys=False, allow_unicode=True)
                
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    print(f"Cleaning Complete.")
    print(f"Files Processed: {total_files}")
    print(f"Total Items Evaluated: {total_items}")
    print(f"Items Actively Cleaned/Fixed: {total_cleaned_items}")

if __name__ == "__main__":
    # If run from scripts folder, go up one dir
    cwd = os.getcwd()
    if os.path.basename(cwd) == 'scripts':
        os.chdir('..')
    
    clean_database()
