"""Inspect contract PDF structure specifically."""
import os
import json
import pdfplumber

files = [
    "raw/L. Crehan - Venice - 1791341 - Contract 09-02.pdf",
    "raw/T. Spiropoulos - Rancho Palos Verdes - 2527258 - Contract 01-10.pdf"
]

for path in files:
    print("\n" + "="*80)
    print("FILE:", os.path.basename(path))
    with pdfplumber.open(path) as pdf:
        print("Total pages:", len(pdf.pages))
        for pg_num in range(min(10, len(pdf.pages))):
            page = pdf.pages[pg_num]
            text = page.extract_text() or ""
            lines = text.split("\n")
            print(f"\n  -- Page {pg_num+1} ({len(lines)} lines) --")
            for l in lines[:40]:
                try:
                    print("    |", l)
                except UnicodeEncodeError:
                    print("    | [unicode error line]")
            if len(lines) > 40:
                print(f"    ... ({len(lines)-40} more lines)")
            
            tables = page.extract_tables()
            if tables:
                print(f"  Tables: {len(tables)}")
                for t_idx, t in enumerate(tables):
                    print(f"    Table {t_idx}: {len(t)} rows")
                    for row in t[:5]:
                        try:
                            print("      ", row)
                        except UnicodeEncodeError:
                            print("       [unicode row]")
