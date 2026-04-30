"""Quick smoke test for the new contract_ingestion.py parser."""
import os
from contract_ingestion import OneClickIngestor

pdfs = [
    r"raw\L. Crehan - Venice - 1791341 - Contract 09-02.pdf",
    r"raw\T. Spiropoulos - Rancho Palos Verdes - 2527258 - Contract 01-10.pdf",
]

for path in pdfs:
    ingestor = OneClickIngestor(path)
    data = ingestor.extract_data()
    items = data.get("line_items", [])
    print("=" * 60)
    print("File  :", os.path.basename(path))
    print("Client:", data["client_name"], " PO:", data["project_po"])
    print("Items :", len(items))
    for item in items[:5]:
        sec  = item.get("section", "")
        cat  = item.get("category", "")
        room = item.get("room", "")
        qty  = item.get("qty", "")
        unit = item.get("unit", "")
        desc = item.get("raw_description", "")[:65]
        print(f"  [{room}] Qty:{qty}{unit} | sec={sec!r} cat={cat!r}")
        print(f"    {desc}")
    print()
