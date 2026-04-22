import json
import re

def compile_matching_rules(product_dict: dict) -> dict:
    rules = {
        "must_contain_regex": [],
        "must_not_contain_regex": [],
        "keywords": []
    }
    
    # 1. Category & Brand
    category = product_dict.get("category", "")
    if category:
        for word in category.split():
            if len(word) > 2:
                rules["keywords"].append(word.lower())
                
    brand = product_dict.get("brand", "")
    if brand:
        rules["keywords"].append(brand.lower())
        
    # 2. Finish Logic
    finish = product_dict.get("finish", "").strip()
    
    finish_groups = {
        "black": ["chrome", "nickel", "gold", "brass", "stainless", "bronze", "white", "polished"],
        "chrome": ["black", "nickel", "gold", "brass", "bronze", "white", "brushed"],
        "nickel": ["black", "chrome", "gold", "brass", "bronze", "white", "polished"],
        "gold": ["black", "chrome", "nickel", "stainless", "bronze", "white"],
        "brass": ["black", "chrome", "nickel", "stainless", "bronze", "white"],
        "bronze": ["black", "chrome", "nickel", "gold", "brass", "stainless", "white"],
        "stainless": ["black", "gold", "brass", "bronze", "white", "polished"],
        "white": ["black", "chrome", "nickel", "gold", "brass", "stainless", "bronze"]
    }
    
    if finish:
        finish_clean = finish.lower().replace(" ", r"\s*")
        rules["must_contain_regex"].append(f"(?i){finish_clean}")
        
        finish_lower = finish.lower()
        exclusions = set()
        for key, conflicts in finish_groups.items():
            if key in finish_lower:
                exclusions.update(conflicts)
        
        if exclusions:
            rules["must_not_contain_regex"].append(f"(?i)({'|'.join(exclusions)})")
            
    # 3. Dimensions Logic
    dims = product_dict.get("dimensions", {})
    if dims:
        for dim_key, dim_val in dims.items():
            dim_str = str(dim_val).strip().lower()
            if not dim_str:
                continue
                
            match = re.search(r'([\d\.]+)\s*(in|inch|"|'')', dim_str)
            if match:
                number = match.group(1)
                rules["must_contain_regex"].append(rf"(?i)\b{number}\s*(in|inch|\"|'')")
                
                common_sizes = {"8", "10", "12", "16", "18", "24", "30", "32", "36", "42", "48", "60", "72"}
                if number in common_sizes:
                    competing = [s for s in common_sizes if s != number]
                    rules["must_not_contain_regex"].append(rf"(?i)\b({'|'.join(competing)})\s*(in|inch|\"|'')")
            else:
                rules["must_contain_regex"].append(f"(?i){re.escape(dim_str)}")
                
    # 4. Description logic for Keywords
    desc = product_dict.get("description", "")
    if desc:
        words = [w.lower() for w in re.findall(r'\b[a-zA-Z]{4,}\b', desc)]
        rules["keywords"].extend(words[:3])
        
    rules["keywords"] = list(set(rules["keywords"]))
    return rules

test_product = {
    'category': 'Grab Bars',
    'brand': '',
    'finish': 'Matte Black',
    'dimensions': {'Width': '16inch', 'Length': '', 'Thickness': ''},
    'description': ''
}

print("16 INCH MATTE BLACK GRAB BAR:")
print(json.dumps(compile_matching_rules(test_product), indent=2))

test_faucet = {
    'category': 'Faucet',
    'brand': 'Moen',
    'finish': 'Brushed Gold',
    'dimensions': {'Spout Height': '8inch'},
    'description': 'Align 1-Handle Faucet'
}

print("\n8 INCH BRUSHED GOLD FAUCET:")
print(json.dumps(compile_matching_rules(test_faucet), indent=2))
