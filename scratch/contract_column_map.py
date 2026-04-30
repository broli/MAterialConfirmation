"""
contract_column_map.py
======================
Precisely maps the x-coordinate column boundaries in the Contract PDFs.
Focuses on pages 1-7 (the item section) of the Contract files.
"""
import os
import pdfplumber

CONTRACT_FILES = [
    "raw/L. Crehan - Venice - 1791341 - Contract 09-02.pdf",
    "raw/T. Spiropoulos - Rancho Palos Verdes - 2527258 - Contract 01-10.pdf"
]

for path in CONTRACT_FILES:
    print("\n" + "="*80)
    print("FILE:", os.path.basename(path))
    with pdfplumber.open(path) as pdf:
        print(f"Total pages: {len(pdf.pages)}")
        for pg_num in range(min(8, len(pdf.pages))):
            page = pdf.pages[pg_num]
            text = page.extract_text() or ""
            lines = text.split("\n")
            
            # Check if this page has item data
            has_items = any(kw in text for kw in ["Bath ", "Kitchen ", "Outside Partner", "1 ea", "sqft", " lft"])
            if not has_items and pg_num > 0:
                print(f"\n  Page {pg_num+1}: [no item data, skipping]")
                continue
            
            print(f"\n  == Page {pg_num+1} ==")
            
            # Print raw text
            for l in lines[:60]:
                try:
                    print(f"    TEXT| {l}")
                except UnicodeEncodeError:
                    print(f"    TEXT| [unicode error]")
            
            # Now print word bounding boxes for ALL words
            words = page.extract_words(keep_blank_chars=False)
            print(f"\n  Word bbox dump ({len(words)} words):")
            print(f"  {'text':30s} {'x0':>7}  {'top':>7}  {'x1':>7}  {'bottom':>7}")
            print(f"  {'-'*60}")
            for w in words[:80]:
                txt = w['text'][:28]
                try:
                    print(f"  {txt:30s} {w['x0']:>7.1f}  {w['top']:>7.1f}  {w['x1']:>7.1f}  {w['bottom']:>7.1f}")
                except UnicodeEncodeError:
                    print(f"  [unicode] {w['x0']:>7.1f}  {w['top']:>7.1f}")
