"""
pdf_diagnostic.py
=================
Analyses every PDF in ./raw and produces a detailed report saved to
scratch/pdf_analysis_results.md.

For each PDF it extracts:
  - Text (page by page)
  - Tables (page by page, via pdfplumber)
  - Words with bounding boxes (first 50 per page)
  - A raw dump of all lines so we can see the real structure

Run from the project root:
  .venv\Scripts\python.exe scratch/pdf_diagnostic.py
"""

import os
import json
import pdfplumber

RAW_DIR = "raw"
OUTPUT_FILE = "scratch/pdf_analysis_results.md"

def analyse_pdf(pdf_path: str) -> dict:
    result = {
        "file": os.path.basename(pdf_path),
        "pages": []
    }

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_data = {
                "page": page_num,
                "text_lines": [],
                "tables": [],
                "words_sample": []
            }

            # ----- 1. Raw text lines -----
            text = page.extract_text()
            if text:
                page_data["text_lines"] = text.split("\n")

            # ----- 2. Tables -----
            tables = page.extract_tables()
            for t_idx, table in enumerate(tables):
                clean_table = []
                for row in table:
                    clean_row = [str(cell).strip() if cell is not None else "" for cell in row]
                    if any(clean_row):  # skip fully-empty rows
                        clean_table.append(clean_row)
                if clean_table:
                    page_data["tables"].append({
                        "table_index": t_idx,
                        "rows": clean_table
                    })

            # ----- 3. Word bounding boxes (first 60) -----
            words = page.extract_words()
            for w in words[:60]:
                page_data["words_sample"].append({
                    "text": w["text"],
                    "x0": round(w["x0"], 1),
                    "top": round(w["top"], 1),
                    "x1": round(w["x1"], 1),
                    "bottom": round(w["bottom"], 1),
                })

            result["pages"].append(page_data)

    return result


def format_table_for_md(table_rows: list) -> str:
    if not table_rows:
        return "_empty table_"
    lines = []
    # header
    header = table_rows[0]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join([" --- " for _ in header]) + "|")
    for row in table_rows[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def main():
    os.makedirs("scratch", exist_ok=True)

    pdf_files = [f for f in os.listdir(RAW_DIR) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print("No PDFs found in ./raw")
        return

    all_results = []
    for fname in sorted(pdf_files):
        path = os.path.join(RAW_DIR, fname)
        print(f"  Analysing: {fname} ...")
        try:
            data = analyse_pdf(path)
            all_results.append(data)
        except Exception as e:
            all_results.append({"file": fname, "error": str(e), "pages": []})

    # ----- Save JSON dump for machine reference -----
    json_path = "scratch/pdf_analysis_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"  JSON saved: {json_path}")

    # ----- Save human-readable Markdown report -----
    lines = ["# PDF Structure Analysis Report\n"]
    lines.append(f"Files analysed: {len(pdf_files)}\n\n---\n")

    for doc in all_results:
        fname = doc["file"]
        lines.append(f"## 📄 {fname}\n")

        if "error" in doc:
            lines.append(f"> **ERROR:** {doc['error']}\n\n")
            continue

        lines.append(f"**Total pages:** {len(doc['pages'])}\n\n")

        for pg in doc["pages"]:
            lines.append(f"### Page {pg['page']}\n")

            # Text
            text_lines = pg["text_lines"]
            if text_lines:
                lines.append("#### Raw Text Lines\n")
                lines.append("```\n")
                for l in text_lines:
                    lines.append(l + "\n")
                lines.append("```\n\n")
            else:
                lines.append("_No text extracted_\n\n")

            # Tables
            if pg["tables"]:
                for t in pg["tables"]:
                    lines.append(f"#### Table {t['table_index'] + 1} ({len(t['rows'])} rows)\n\n")
                    lines.append(format_table_for_md(t["rows"]) + "\n\n")
            else:
                lines.append("_No tables detected on this page_\n\n")

            # Words sample
            if pg["words_sample"]:
                lines.append("#### Word Bounding Boxes (first 60)\n\n")
                lines.append("| text | x0 | top | x1 | bottom |\n")
                lines.append("|---|---|---|---|---|\n")
                for w in pg["words_sample"]:
                    lines.append(f"| {w['text']} | {w['x0']} | {w['top']} | {w['x1']} | {w['bottom']} |\n")
                lines.append("\n")

            lines.append("---\n\n")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"\n✅ Done! Markdown report: {OUTPUT_FILE}")
    print(f"   JSON dump:        {json_path}")


if __name__ == "__main__":
    main()
