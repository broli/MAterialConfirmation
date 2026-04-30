"""
parse_contract_test.py
======================
Tests x-coordinate column parsing SPECIFICALLY for Contract PDFs.

Contract PDF column layout (confirmed from bounding box analysis):
  x ≈  107        Section   ("Bath", "Kitchen", "Outside Partner")
  x ≈  131-215    Category  ("Bathroom Labor", "Shower Bases", "Accessories", ...)
  x ≈  216-540    Description (item name, flowing across the page)
  x ≈  550-558    Qty  (always right-aligned near x=550)
  x ≈  559-572    Unit ("ea", "sqft", "lft", "lf")

Item header rows (the triggering row):
  Section Category  Description...short...  Qty Unit
  
Continuation rows (description overflow):
  (same description area, no qty/unit)

Room change markers:
  "Bath 2", "Bath 3", "kitchen remodel", etc. — appear as short lines
  identified by: section word alone, or "Bath N" as x≈39 word + digit

Stop markers:
  "Customer Information", "Bathroom Worksheet", "Included Subtotal" at end of section
"""

import os
import json
import re
import pdfplumber

RAW_DIR = "raw"

# x-coordinate thresholds for the CONTRACT pdf layout
# (confirmed empirically from bounding box dump above)
SECTION_MIN_X  = 100   # "Bath", "Kitchen", "Outside Partner" start here
SECTION_MAX_X  = 135   # section words are short
CATEGORY_MIN_X = 130
CATEGORY_MAX_X = 220
DESC_MIN_X     = 215
DESC_MAX_X     = 545
QTY_MIN_X      = 545   # qty number sits at x≈550
UNIT_MIN_X     = 555   # unit "ea/sqft/lft" sits at x≈559

# Room-change markers that appear at x≈39 (left margin, larger font)
ROOM_MARKER_X  = 45    # "Bath 2" appears at x≈39

# Valid units
VALID_UNITS = {"ea", "sqft", "lft", "lf"}

# Lines/sections that mark the end of item data
END_MARKERS = {
    "customer information",
    "bathroom worksheet",
    "acknowledgements",
    "payment schedule",
    "california home improvement agreement",
    "pre-installation acknowledgements",
}

# Header lines to skip
SKIP_TEXTS = {
    "product quantity",
    "included",
}


def bucket_word(x0: float) -> str:
    if x0 < ROOM_MARKER_X:
        return "left_margin"       # room change labels ("Bath 2")
    if SECTION_MIN_X <= x0 < SECTION_MAX_X:
        return "section"
    if CATEGORY_MIN_X <= x0 < CATEGORY_MAX_X:
        return "category"
    if DESC_MIN_X <= x0 < DESC_MAX_X:
        return "description"
    if x0 >= QTY_MIN_X and x0 < UNIT_MIN_X:
        return "qty"
    if x0 >= UNIT_MIN_X:
        return "unit"
    return "other"


def group_words_by_row(words: list, tolerance: float = 3.0) -> list:
    """Group words into visual rows by y-position proximity."""
    if not words:
        return []
    rows = {}
    for w in words:
        key = round(w["top"] / tolerance) * tolerance
        rows.setdefault(key, []).append(w)
    return [sorted(row, key=lambda w: w["x0"]) for row in sorted(rows.values(), key=lambda r: r[0]["top"])]


def parse_contract_pdf(path: str) -> dict:
    result = {
        "file": os.path.basename(path),
        "client_name": "",
        "project_po": "",
        "line_items": [],
    }

    current_room = "Bath 1"
    current_item = None
    found_header = False
    stop = False

    def flush_item():
        nonlocal current_item
        if current_item:
            # Combine all parts into one clean description
            parts = [
                current_item.get("section", ""),
                current_item.get("category", ""),
                current_item.get("raw_description", ""),
            ]
            combined = " ".join(p for p in parts if p).strip()
            combined = re.sub(r"\s+", " ", combined)
            current_item["raw_description"] = combined
            result["line_items"].append(current_item)
        current_item = None

    with pdfplumber.open(path) as pdf:
        # ── Header extraction (page 1 = cover page, page 3 = first item page) ──
        # Page 1 has "Prepared for:" block
        p1_text = pdf.pages[0].extract_text() or ""
        name_match = re.search(r"Prepared for:\s*\n([A-Za-z ,'-]+)\n", p1_text)
        if name_match:
            result["client_name"] = name_match.group(1).strip()

        # PO is on page 3 header area ("Copy of 1791341" or just the number)
        p3_text = pdf.pages[2].extract_text() if len(pdf.pages) > 2 else ""
        po_match = re.search(r"(?:Copy of\s+)?(\d{6,})", p3_text or "")
        if po_match:
            result["project_po"] = po_match.group(1)

        # ── Item extraction: pages 3..N until stop marker ──────────────────────
        for page_num, page in enumerate(pdf.pages):
            if stop:
                break
            
            # Skip cover/legal pages (1 and 2) — items start on page 3
            if page_num < 2:
                continue

            words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
            rows = group_words_by_row(words, tolerance=3.0)

            for row_words in rows:
                line_text = " ".join(w["text"] for w in row_words).strip()
                low = line_text.lower()

                # ── Stop detection ────────────────────────────────────────────
                if any(m in low for m in END_MARKERS):
                    stop = True
                    break

                # ── Skip header rows ──────────────────────────────────────────
                if any(low == s for s in SKIP_TEXTS):
                    found_header = True
                    continue

                if not found_header:
                    # Look for "Product Quantity" header to know items begin
                    if "product" in low and "quantity" in low:
                        found_header = True
                    continue

                # ── Skip subtotal / section summary lines ─────────────────────
                if "subtotal" in low and "$" in low:
                    continue

                # ── Room change detection ─────────────────────────────────────
                # Room labels are short lines at x≈39 (left of item indent)
                # e.g. "Bath 2", "Bath 3", "kitchen remodel", "Bath 1" (after "Included")
                left_margin_words = [w for w in row_words if w["x0"] < SECTION_MIN_X]
                if left_margin_words and len(row_words) <= 4:
                    room_candidate = " ".join(w["text"] for w in row_words).strip()
                    # Short line, likely a room header
                    if len(room_candidate) <= 20:
                        flush_item()
                        current_room = room_candidate
                        continue

                # ── Classify words into columns ───────────────────────────────
                buckets = {"section": [], "category": [], "description": [],
                           "qty": [], "unit": [], "left_margin": [], "other": []}
                for w in row_words:
                    b = bucket_word(w["x0"])
                    buckets[b].append(w["text"])

                section_txt = " ".join(buckets["section"]).strip()
                category_txt = " ".join(buckets["category"]).strip()
                desc_txt = " ".join(buckets["description"]).strip()
                qty_txt = " ".join(buckets["qty"]).strip()
                unit_txt = " ".join(buckets["unit"]).strip().lower()

                # A new item starts when qty + valid unit are present on the row
                if qty_txt and unit_txt in VALID_UNITS:
                    flush_item()
                    current_item = {
                        "room": current_room,
                        "section": section_txt,
                        "category": category_txt,
                        "raw_description": desc_txt,
                        "qty": int(qty_txt) if qty_txt.isdigit() else qty_txt,
                        "unit": unit_txt,
                        "continuation_lines": [],
                    }
                elif current_item is not None:
                    # Continuation: append description overflow lines
                    cont = f"{section_txt} {category_txt} {desc_txt}".strip()
                    cont = re.sub(r"\s+", " ", cont)
                    if cont:
                        current_item["continuation_lines"].append(cont)

        flush_item()

    # Merge continuation lines
    for item in result["line_items"]:
        cont = item.pop("continuation_lines", [])
        if cont:
            item["raw_description"] = item["raw_description"] + " " + " ".join(cont)
        item["raw_description"] = re.sub(r"\s+", " ", item["raw_description"]).strip()

    return result


def main():
    os.makedirs("scratch", exist_ok=True)

    contract_files = [
        f for f in os.listdir(RAW_DIR)
        if f.lower().endswith(".pdf") and "contract" in f.lower()
    ]

    if not contract_files:
        print("No Contract PDFs found in ./raw — looking for files with 'contract' in name")
        # Fall back to all PDFs
        contract_files = [f for f in os.listdir(RAW_DIR) if f.lower().endswith(".pdf")]

    all_results = []
    for fname in sorted(contract_files):
        path = os.path.join(RAW_DIR, fname)
        print(f"\n{'='*70}")
        print(f"Parsing: {fname}")
        try:
            parsed = parse_contract_pdf(path)
            all_results.append(parsed)
            print(f"  Client : {parsed['client_name']}")
            print(f"  PO     : {parsed['project_po']}")
            print(f"  Items  : {len(parsed['line_items'])}")
            for item in parsed["line_items"]:
                desc = item["raw_description"]
                if len(desc) > 95:
                    desc = desc[:92] + "..."
                print(f"    [{item['room']}] Qty:{item['qty']}{item['unit']} | {desc}")
        except Exception as e:
            import traceback
            print(f"  ERROR: {e}")
            traceback.print_exc()

    out = "scratch/contract_parse_output.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
