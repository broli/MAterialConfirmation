import os
import json
from client_pdf_generator import PDFGenerator
from catalog_loader import CatalogLoader

loader = CatalogLoader(base_path="database")
catalog = loader.load_all_categories()

payload = {
    "client_info": {
        "name": "Test Grid Layout",
        "project": "PO 12345"
    },
    "products": []
}

count = 0
for db_id, item in catalog.items():
    if "printable" in item and item["printable"]:
        test_item = item.copy()
        test_item["room"] = "Bathroom"
        test_item["qty"] = 1
        payload["products"].append(test_item)
        count += 1
        if count >= 5:
            break

gen = PDFGenerator(base_path="database", output_path="output")
gen.create_pdf(payload)
print("Done")
