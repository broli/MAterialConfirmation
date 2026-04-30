"""
contract_ingestion.py
=====================
Handles PDF ingestion for OneClick contract PDFs (the source of truth).

The parser uses x-coordinate column detection to reliably extract structured
line items from the contract's fixed-layout page format.

CONTRACT PDF COLUMN MAP (confirmed via bounding box analysis on real files):
    x ≈ 107        Section     "Bath", "Kitchen", "Outside Partner"
    x ≈ 131–220    Category    "Shower Bases", "Bathroom Labor", "Accessories"
    x ≈ 215–545    Description  Full item text (may span continuation lines)
    x ≈ 550–558    Qty          Right-aligned integer ("1", "5", "60")
    x ≈ 559–572    Unit         "ea", "sqft", "lft", "lf"

Room changes appear at x ≈ 39 (left of item indent): "Bath 2", "Bath 3", etc.
Stop markers: "Customer Information", "Bathroom Worksheet", "Payment Schedule".

Public API (unchanged)
-----------------------
    ingestor = OneClickIngestor(pdf_path, debug_mode=False)
    data = ingestor.extract_data()
    # data = {
    #     "client_name": str,
    #     "project_po":  str,
    #     "line_items": [
    #         {
    #             "room":            str,   # e.g. "Bath 1", "Bath 2"
    #             "section":         str,   # e.g. "Bath", "Kitchen"   (NEW)
    #             "category":        str,   # e.g. "Shower Bases"      (NEW)
    #             "raw_description": str,
    #             "qty":             int,
    #             "unit":            str,   # "ea" / "sqft" / "lft"   (NEW)
    #         },
    #         ...
    #     ]
    # }
"""

import os
import re
import time
import logging
import pdfplumber


# ─── x-boundary thresholds (contract PDF layout) ────────────────────────────
_ROOM_LABEL_MAX_X   = 50    # "Bath 2", "Bath 3" live at x ≈ 39
_SECTION_MIN_X      = 100   # "Bath", "Kitchen", "Outside Partner"
_SECTION_MAX_X      = 130   # Section is just 1 word; next word (category) starts at ~131
_CATEGORY_MIN_X     = 130
_CATEGORY_MAX_X     = 183   # Category 1-2 words; description starts at ~183-215
_DESC_MIN_X         = 183
_DESC_MAX_X         = 545
_QTY_MIN_X          = 545   # qty number sits at x ≈ 550
_UNIT_MIN_X         = 555   # unit sits at x ≈ 559

_VALID_UNITS        = {"ea", "sqft", "lft", "lf"}

# Lines that mark the definitive end of item data
_END_MARKERS = {
    "customer information",
    "bathroom worksheet",
    "acknowledgements",
    "payment schedule",
    "california home improvement agreement",
    "pre-installation acknowledgements",
}

# Structural header lines to silently skip
_SKIP_EXACT = {
    "product quantity",
    "included",
}

# Room-level section starters — when these appear as isolated short lines at
# the left margin they are treated as room-change signals, not items.
_SECTION_KEYWORDS = {"bath", "kitchen", "outside partner", "dates", "notes"}

# Sections whose items we do NOT ingest (scheduling / legal / financing)
_STOP_ROOM_LABELS = {"dates"}


# ─── helpers ─────────────────────────────────────────────────────────────────

def _bucket(x0: float) -> str:
    """Map a word's x-position to a logical column name."""
    if x0 < _ROOM_LABEL_MAX_X:
        return "room_label"
    if _SECTION_MIN_X <= x0 < _SECTION_MAX_X:
        return "section"
    if _CATEGORY_MIN_X <= x0 < _CATEGORY_MAX_X:
        return "category"
    if _DESC_MIN_X <= x0 < _DESC_MAX_X:
        return "description"
    if _QTY_MIN_X <= x0 < _UNIT_MIN_X:
        return "qty"
    if x0 >= _UNIT_MIN_X:
        return "unit"
    return "other"


def _group_rows(words: list, tolerance: float = 3.0) -> list:
    """Group extracted words into visual rows by y-position proximity."""
    rows: dict = {}
    for w in words:
        key = round(w["top"] / tolerance) * tolerance
        rows.setdefault(key, []).append(w)
    return [
        sorted(row, key=lambda w: w["x0"])
        for row in sorted(rows.values(), key=lambda r: r[0]["top"])
    ]


# ─── main class ──────────────────────────────────────────────────────────────

class OneClickIngestor:
    """
    Extracts structured line items from a OneClick contract PDF.

    Parameters
    ----------
    pdf_path : str
        Absolute path to the contract PDF file.
    debug_mode : bool
        When True, writes a detailed diagnostic Markdown report to
        a ``Debug/`` folder next to the PDF.
    """

    def __init__(self, pdf_path: str, debug_mode: bool = False):
        self.pdf_path   = pdf_path
        self.target_dir = os.path.dirname(pdf_path) if pdf_path else "."
        self.debug_mode = debug_mode
        self.logger     = self._setup_logger()

    # ------------------------------------------------------------------
    # Logger setup
    # ------------------------------------------------------------------

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger("ContractIngestion")
        for h in logger.handlers[:]:
            logger.removeHandler(h)

        if self.debug_mode:
            log_dir = os.path.join(self.target_dir, "Debug")
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, "ingestion_debug.log")
            logger.setLevel(logging.DEBUG)
        else:
            os.makedirs("logs", exist_ok=True)
            log_path = "logs/ingestion_debug.log"
            logger.setLevel(logging.INFO)

        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(fh)
        return logger

    def refresh_logger(self, debug_mode: bool) -> None:
        """Allow dynamic switching of log targets mid-session."""
        self.debug_mode = debug_mode
        self.logger = self._setup_logger()
        self.logger.info(f"Logger refreshed. Debug mode: {self.debug_mode}")

    # ------------------------------------------------------------------
    # Public extraction API
    # ------------------------------------------------------------------

    def extract_data(self) -> dict:
        """
        Parse the contract PDF and return structured data.

        Returns
        -------
        dict
            ``{"client_name": str, "project_po": str, "line_items": list}``
            Returns an empty dict if the file is missing or unreadable.
        """
        if not self.pdf_path or not os.path.exists(self.pdf_path):
            self.logger.error("Invalid or missing PDF file path.")
            return {}
        return self._parse_pdf(self.pdf_path)

    # ------------------------------------------------------------------
    # Internal parser
    # ------------------------------------------------------------------

    def _parse_pdf(self, pdf_path: str) -> dict:
        self.logger.info(f"Parsing contract PDF: {pdf_path}")
        t_start = time.perf_counter()

        result = {"client_name": "", "project_po": "", "line_items": []}
        debug_lines = [
            "# Ingestion Diagnostic Report\n",
            f"**Source**: `{os.path.basename(pdf_path)}`\n\n---\n",
        ]

        try:
            with pdfplumber.open(pdf_path) as pdf:
                # ── Metadata extraction ───────────────────────────────────────
                # Page 0 = cover: "Prepared for:\nLastname, First"
                p0_text = pdf.pages[0].extract_text() or ""
                name_m = re.search(r"Prepared for:\s*\n([A-Za-z ,'-]+)\n", p0_text)
                if name_m:
                    result["client_name"] = name_m.group(1).strip()

                # Page 2 (index 2) = first items page; PO lives in the header
                p2_text = pdf.pages[2].extract_text() if len(pdf.pages) > 2 else ""
                po_m = re.search(r"(?:Copy of\s+)?(\d{6,})", p2_text or "")
                if po_m:
                    result["project_po"] = po_m.group(1)

                # Filename fallback for PO / client when header extraction fails
                base = os.path.basename(pdf_path)
                if not result["project_po"]:
                    fb = re.search(r"(\d{5,})", base)
                    if fb:
                        result["project_po"] = fb.group(1)
                if not result["client_name"]:
                    result["client_name"] = re.split(r"[-_]", base)[0].strip()

                debug_lines.append(f"**Client**: `{result['client_name']}`\n")
                debug_lines.append(f"**PO**: `{result['project_po']}`\n\n---\n")
                debug_lines.append("## Line Items\n\n")

                # ── Item extraction ───────────────────────────────────────────
                current_room = "Bath 1"   # first room is unnamed by convention
                current_item: dict | None = None
                found_header  = False
                stop          = False

                def flush() -> None:
                    nonlocal current_item
                    if not current_item:
                        return
                    # Merge continuation lines into the description
                    cont = current_item.pop("_cont", [])
                    if cont:
                        current_item["raw_description"] = (
                            current_item["raw_description"]
                            + " "
                            + " ".join(cont)
                        )
                    current_item["raw_description"] = re.sub(
                        r"\s+", " ", current_item["raw_description"]
                    ).strip()

                    debug_lines.append(
                        f"- **[{current_item['room']}]** "
                        f"Qty:{current_item['qty']}{current_item['unit']} | "
                        f"{current_item['raw_description'][:80]}\n"
                    )
                    result["line_items"].append(current_item)
                    current_item = None

                # Items start on page index 2; skip cover and legal pages
                for page_idx, page in enumerate(pdf.pages):
                    if stop:
                        break
                    if page_idx < 2:
                        continue

                    words = page.extract_words(
                        keep_blank_chars=False, use_text_flow=False
                    )
                    rows = _group_rows(words, tolerance=3.0)

                    for row_words in rows:
                        line_text = " ".join(w["text"] for w in row_words).strip()
                        low = line_text.lower()

                        # ── Stop detection ────────────────────────────────────
                        if any(m in low for m in _END_MARKERS):
                            flush()
                            stop = True
                            debug_lines.append("\n**Stop marker detected.**\n")
                            break

                        # ── Skip structural headers ───────────────────────────
                        if low in _SKIP_EXACT:
                            if "product" in low and "quantity" in low:
                                found_header = True
                            continue

                        # ── "Product Quantity" header marks start of items ────
                        if "product" in low and "quantity" in low:
                            found_header = True
                            continue

                        if not found_header:
                            continue

                        # ── Skip subtotal summary lines ───────────────────────
                        if "subtotal" in low and "$" in low:
                            continue

                        # ── Classify words by column ──────────────────────────
                        buckets: dict[str, list] = {
                            b: [] for b in
                            ("room_label", "section", "category",
                             "description", "qty", "unit", "other")
                        }
                        for w in row_words:
                            buckets[_bucket(w["x0"])].append(w["text"])

                        section_txt  = " ".join(buckets["section"]).strip()
                        category_txt = " ".join(buckets["category"]).strip()
                        desc_txt     = " ".join(buckets["description"]).strip()
                        qty_txt      = " ".join(buckets["qty"]).strip()
                        unit_txt     = " ".join(buckets["unit"]).strip().lower()
                        label_words  = buckets["room_label"]

                        # ── Room-change detection ─────────────────────────────
                        # Room labels appear at x<50, short lines (≤4 words total)
                        if label_words and len(row_words) <= 4:
                            room_candidate = " ".join(
                                w["text"] for w in row_words
                            ).strip()
                            if len(room_candidate) <= 25:
                                flush()
                                # Stop ingesting items from scheduling sections
                                if room_candidate.lower() in _STOP_ROOM_LABELS:
                                    stop = True
                                    debug_lines.append(
                                        f"\n**Room '{room_candidate}' is a stop section.**\n"
                                    )
                                    break
                                current_room = room_candidate
                                debug_lines.append(
                                    f"\n### Room: {current_room}\n\n"
                                )
                                continue

                        # ── New item: row has qty + valid unit ────────────────
                        if qty_txt and unit_txt in _VALID_UNITS:
                            flush()
                            full_desc = " ".join(
                                p for p in (section_txt, category_txt, desc_txt) if p
                            ).strip()
                            try:
                                qty_int = int(qty_txt)
                            except ValueError:
                                qty_int = 0

                            current_item = {
                                "room":            current_room,
                                "section":         section_txt,
                                "category":        category_txt,
                                "raw_description": full_desc,
                                "qty":             qty_int,
                                "unit":            unit_txt,
                                "_cont":           [],
                            }

                        elif current_item is not None:
                            # ── Continuation line for the current item ────────
                            cont = " ".join(
                                p for p in (section_txt, category_txt, desc_txt) if p
                            ).strip()
                            # Ignore page-footer repetition (company name lines)
                            if cont and "payless kitchen" not in cont.lower():
                                current_item["_cont"].append(cont)

                # End of all pages — flush the last open item
                flush()

        except Exception as exc:
            self.logger.error(f"Error parsing PDF: {exc}", exc_info=True)
            return result

        # ── Debug report ──────────────────────────────────────────────────────
        if self.debug_mode:
            log_dir = os.path.join(self.target_dir, "Debug")
            os.makedirs(log_dir, exist_ok=True)
            debug_lines.append(
                f"\n\n**Total items extracted: {len(result['line_items'])}**\n"
            )
            with open(
                os.path.join(log_dir, "ingestion_result.md"), "w", encoding="utf-8"
            ) as f:
                f.writelines(debug_lines)

        self.logger.info(
            f"Extracted {len(result['line_items'])} items "
            f"(PO={result['project_po']}, Client={result['client_name']}) "
            f"in {time.perf_counter() - t_start:.2f}s"
        )
        return result
