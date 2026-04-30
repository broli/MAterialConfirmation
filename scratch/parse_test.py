"""
parse_test.py
=============
Tests the x-coordinate based column parser against all PDFs in ./raw.
Saves results to scratch/parse_test_output.json and prints summary.
"""
import os
import json
import re
import pdfplumber

RAW_DIR = "raw"

# ─── Column x-boundaries (measured from bounding box analysis) ────────────────
# The line items area has these approximate x-positions for each column:
#   Col A "Section"    x0 ≈  28  (e.g., "Bath", "Kitchen", "Outside Partner")
#   Col B "Category"   x0 ≈  43  (e.g., "Shower Bases", "Flooring")
#   Col C "SKU"        x0 ≈  94
#   Col D "Description" x0 ≈ 139
#   Col E "Qty"        x0 ≈ 228
#   Col F "Unit"       x0 ≈ 234  (e.g., "ea", "sqft", "lft")
#   Col G "Labor Price" x0 ≈ 295
#   Col H "Unit Price" x0 ≈ 362
# We use x-thresholds to bucket words into columns.

SECTION_X    = (20,  42)   # "Bath", "Kitchen", "Outside Partner", "notes"
CATEGORY_X   = (42,  94)   # "Shower Bases", "Flooring"
SKU_X        = (94,  139)  # SKU codes
DESCRIPTION_X= (139, 228)  # The main text description
QTY_X        = (225, 234)  # Qty number
UNIT_X       = (234, 265)  # ea / sqft / lft / lf
PRICE_X      = (265, 600)  # All price columns — we don't care about these

# Stop-words that mark the end of the items section
END_MARKERS = {"customer information", "bathroom worksheet", "acknowledgements"}

# Header rows to skip
HEADER_TEXTS = {
    "product sku description qty labor price unit price ext price unit cost ext cost",
    "included",
    "product quantity",
}

def bucket_word(x0: float) -> str:
    if SECTION_X[0] <= x0 < SECTION_X[1]:
        return "section"
    if CATEGORY_X[0] <= x0 < CATEGORY_X[1]:
        return "category"
    if SKU_X[0] <= x0 < SKU_X[1]:
        return "sku"
    if DESCRIPTION_X[0] <= x0 < DESCRIPTION_X[1]:
        return "description"
    if QTY_X[0] <= x0 < QTY_X[1]:
        return "qty"
    if UNIT_X[0] <= x0 < UNIT_X[1]:
        return "unit"
    return "other"


def parse_pdf(path: str) -> dict:
    """Parse a OneClick contract PDF into structured line items."""
    result = {
        "file": os.path.basename(path),
        "client_name": "",
        "project_po": "",
        "line_items": [],
        "debug_pages": []
    }

    current_room = "Bath 1"
    current_item = None
    found_header = False
    stop = False

    with pdfplumber.open(path) as pdf:
        # ── Header extraction (page 1 only) ──────────────────────────────────
        first_text = pdf.pages[0].extract_text() or ""
        po_match = re.search(r"(?:Copy of\s+)?(\d{6,})", first_text)
        if po_match:
            result["project_po"] = po_match.group(1)

        # Name appears after "Estimate Details\n" or alone on its line
        name_match = re.search(
            r"Estimate Details\s*\n([A-Za-z ,'-]+)\n",
            first_text
        )
        if name_match:
            result["client_name"] = name_match.group(1).strip()
        else:
            # Try "LastName, FirstName" anywhere
            name_match2 = re.search(r"\n([A-Z][a-z]+,\s+[A-Z][a-z]+)\n", first_text)
            if name_match2:
                result["client_name"] = name_match2.group(1).strip()

        # ── Line item extraction (all pages, word-bbox approach) ──────────────
        for page in pdf.pages:
            if stop:
                break

            words = page.extract_words(keep_blank_chars=False, use_text_flow=False)

            # Group words by y-band (same "row" = within 3pt of each other)
            rows = {}
            for w in words:
                row_key = round(w["top"] / 3) * 3
                rows.setdefault(row_key, []).append(w)

            for row_key in sorted(rows.keys()):
                row_words = sorted(rows[row_key], key=lambda w: w["x0"])

                # Build full line text for stop / skip detection
                line_text = " ".join(w["text"] for w in row_words).strip()
                low = line_text.lower()

                if any(m in low for m in END_MARKERS):
                    stop = True
                    break

                if any(low == h for h in HEADER_TEXTS):
                    found_header = True
                    continue

                if not found_header:
                    continue  # Skip preamble

                # Skip separator lines
                if re.match(r"^[-─=]{4,}$", line_text):
                    continue

                # ── Classify words by column ──────────────────────────────────
                buckets = {"section": [], "category": [], "sku": [],
                           "description": [], "qty": [], "unit": [], "other": []}

                for w in row_words:
                    b = bucket_word(w["x0"])
                    buckets[b].append(w["text"])

                section_txt  = " ".join(buckets["section"]).strip()
                category_txt = " ".join(buckets["category"]).strip()
                desc_txt     = " ".join(buckets["description"]).strip()
                qty_txt      = " ".join(buckets["qty"]).strip()
                unit_txt     = " ".join(buckets["unit"]).strip().lower()

                # Room change: section word + category word, but NO qty/unit
                if section_txt and not qty_txt and not unit_txt:
                    # Could be continuation of previous item's description,
                    # or a new room header.
                    # Room headers are short lines that contain only section/category
                    is_likely_room = (
                        section_txt.lower() in ("bath", "kitchen", "notes", "outside partner")
                        and category_txt
                        and len(category_txt.split()) <= 4
                        and not desc_txt
                    )
                    if is_likely_room:
                        room_candidate = f"{section_txt} {category_txt}".strip()
                        if room_candidate.lower() != current_item.get("category", "").lower() if current_item else True:
                            current_room = room_candidate
                        continue

                # A new line item starts when we see a qty + unit
                if qty_txt and unit_txt and unit_txt in ("ea", "sqft", "lft", "lf"):
                    # Flush previous item
                    if current_item:
                        result["line_items"].append(current_item)

                    full_desc = f"{section_txt} {category_txt} {desc_txt}".strip()
                    current_item = {
                        "room": current_room,
                        "section": section_txt,
                        "category": category_txt,
                        "raw_description": full_desc,
                        "qty": int(qty_txt),
                        "unit": unit_txt,
                        "continuation_lines": []
                    }
                else:
                    # Continuation lines for the current item
                    cont = f"{section_txt} {category_txt} {desc_txt}".strip()
                    if cont and current_item:
                        current_item["continuation_lines"].append(cont)

        # Flush last item
        if current_item:
            result["line_items"].append(current_item)

    # Merge continuation lines into raw_description
    for item in result["line_items"]:
        cont = item.pop("continuation_lines", [])
        if cont:
            item["raw_description"] = item["raw_description"] + " " + " ".join(cont)
        # Clean up whitespace
        item["raw_description"] = re.sub(r"\s+", " ", item["raw_description"]).strip()

    return result


def main():
    os.makedirs("scratch", exist_ok=True)
    pdfs = sorted([f for f in os.listdir(RAW_DIR) if f.lower().endswith(".pdf")])
    all_results = []

    for fname in pdfs:
        path = os.path.join(RAW_DIR, fname)
        print(f"\nParsing: {fname}")
        try:
            parsed = parse_pdf(path)
            all_results.append(parsed)
            print(f"  Client: {parsed['client_name']}")
            print(f"  PO    : {parsed['project_po']}")
            print(f"  Items : {len(parsed['line_items'])}")
            for item in parsed["line_items"]:
                print(f"    [{item['room']}] Qty:{item['qty']}{item['unit']} | {item['raw_description'][:90]}")
        except Exception as e:
            import traceback
            print(f"  ERROR: {e}")
            traceback.print_exc()
            all_results.append({"file": fname, "error": str(e)})

    out = "scratch/parse_test_output.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
