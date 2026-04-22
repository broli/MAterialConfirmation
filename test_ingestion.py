from contract_ingestion import OneClickIngestor
import json

files_to_test = [
    "raw/Spiropoulos Troy_ Bath - ESTIMATE DETAILS.pdf",
    "raw/T. Spiropoulos - Rancho Palos Verdes - 2527258 - Contract 01-10.pdf",
    "raw/L. Crehan - Venice - 1791341 - Contract 09-02.pdf"
]

for f in files_to_test:
    print(f"\n--- Testing {f} ---")
    ingestor = OneClickIngestor(f)
    res = ingestor.extract_data()
    print(f"Client: {res.get('client_name')}")
    print(f"PO: {res.get('project_po')}")
    items = res.get('line_items', [])
    print(f"Total items extracted: {len(items)}")
    for i, it in enumerate(items):
        desc = it.get('raw_description', '')
        if len(desc) > 60:
            desc = desc[:57] + "..."
        print(f"  {i+1}. Room: {it.get('room')} | Qty: {it.get('qty')} | Desc: {desc}".encode("ascii", "ignore").decode())
