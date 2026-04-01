import yaml
import os
from catalog_loader import CatalogLoader

class SessionManager:
    def __init__(self, catalog_loader_instance):
        # We pass the loaded database into this manager
        self.catalog = catalog_loader_instance.master_catalog
        self.sessions_path = "sessions"

    def process_client_session(self, filename):
        """Reads a client session and pulls the full product data from the catalog."""
        file_path = os.path.join(self.sessions_path, filename)
        
        if not os.path.exists(file_path):
            print(f"❌ Error: Session file '{filename}' not found.")
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                session_data = yaml.safe_load(f)
        except Exception as e:
            print(f"❌ Error reading session YAML: {e}")
            return None

        # Prepare the final data payload for the PDF Generator
        ready_for_pdf = {
            "client_info": session_data.get("client_info", {}),
            "products": []
        }

        print(f"\nProcessing session for: {ready_for_pdf['client_info'].get('name', 'Unknown Client')}")
        
        # Match IDs to the Catalog
        missing_items = 0
        for item in session_data.get("selected_items", []):
            product_id = item.get("id")
            
            if product_id in self.catalog:
                ready_for_pdf["products"].append(self.catalog[product_id])
                print(f"  ✅ Found: {product_id} ({self.catalog[product_id]['model']})")
            else:
                print(f"  ⚠️ WARNING: Product ID '{product_id}' not found in master catalog!")
                missing_items += 1

        if missing_items > 0:
            print(f"\n⚠️ Proceed with caution: {missing_items} items were missing from the database.")
        else:
            print("\n✅ All client selections verified and loaded successfully.")

        return ready_for_pdf

# --- Test Execution ---
if __name__ == "__main__":
    from pdf_engine import PDFGenerator  # Import the PDF engine
    
    # 1. Boot up the Database (Module 1)
    print("--- 1. Loading Master Catalog ---")
    db_loader = CatalogLoader()
    db_loader.load_all_categories()
    
    # 2. Process the Client Session (Module 2)
    print("\n--- 2. Processing Client Session ---")
    session_mgr = SessionManager(db_loader)
    pdf_payload = session_mgr.process_client_session("test_client.yaml")
    
    # 3. Generate the PDF (Module 3)
    if pdf_payload and pdf_payload.get("products"):
        print("\n--- 3. Generating PDF Document ---")
        pdf_maker = PDFGenerator()
        pdf_maker.create_pdf(pdf_payload)
    else:
        print("\n❌ No data payload available to generate PDF.")