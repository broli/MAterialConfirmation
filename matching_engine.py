from rapidfuzz import process, fuzz

class MatchingEngine:
    def __init__(self, catalog):
        """
        Initializes the matching engine with the master catalog.
        The catalog should be a dictionary of id -> item_data.
        """
        self.catalog = catalog
        self.reference_descriptions = {}
        
        # Build lookup table mapping the expected oneclick_description to the item ID
        for item_id, item_data in self.catalog.items():
            desc = item_data.get("oneclick_description", "")
            if desc:
                # If multiple IDs share the same oneclick_description, this simplified
                # implementation overwrites. In a production scenario, you might map 
                # a unique key combining brand/model/finish to IDs.
                self.reference_descriptions[item_id] = desc
            else:
                # Fallback: Create a fuzzy string from brand, model, type, finish
                fallback_desc = f"{item_data.get('brand', '')} {item_data.get('model', '')} {item_data.get('type', '')} {item_data.get('finish', '')}".strip()
                self.reference_descriptions[item_id] = fallback_desc

    def match_item(self, extracted_text):
        """
        Matches extracted text against the catalog.
        Returns a tuple: (best_match_id, best_match_string, confidence_score)
        """
        if not self.reference_descriptions:
            return None, None, 0.0

        choices = {item_id: desc for item_id, desc in self.reference_descriptions.items()}
        
        # extracted_text might be messy, so we use WRatio which handles different lengths well
        result = process.extractOne(extracted_text, choices, scorer=fuzz.WRatio)
        
        if result:
            best_match_string, confidence_score, best_match_id = result
            return best_match_id, best_match_string, confidence_score
            
        return None, None, 0.0

    def get_color_code(self, score):
        """Returns the PM verification color code based on the score."""
        if score == 100.0:
            return "green"
        elif score >= 90.0:
            return "yellow"
        else:
            return "red"
