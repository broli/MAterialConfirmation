import os
import glob
import pdfplumber
import re
import logging

class OneClickIngestor:
    def __init__(self, target_directory, debug_mode=False):
        self.target_dir = target_directory
        self.debug_mode = debug_mode
        self.logger = self._setup_logger()

    def _setup_logger(self):
        logger = logging.getLogger("ContractIngestion")
        
        # Clear existing handlers to allow redirection
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            
        if self.debug_mode:
            log_dir = os.path.join(self.target_dir, "Debug")
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, "ingestion_debug.log")
            logger.setLevel(logging.DEBUG)
        else:
            os.makedirs("logs", exist_ok=True)
            log_path = "logs/ingestion_debug.log"
            logger.setLevel(logging.INFO)

        fh = logging.FileHandler(log_path)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        return logger

    def refresh_logger(self, debug_mode):
        """Allows dynamic switching of log targets mid-session."""
        self.debug_mode = debug_mode
        self.logger = self._setup_logger()
        self.logger.info(f"Logger refreshed. Debug mode: {self.debug_mode}")

    def extract_data(self):
        """Scans the target directory for Contract and Estimate PDFs and extracts data."""
        self.logger.info(f"Starting extraction in directory: {self.target_dir}")
        pdf_files = glob.glob(os.path.join(self.target_dir, "*.pdf"))
        
        estimate_pdf = None
        contract_pdf = None
        
        for p in pdf_files:
            lower_name = os.path.basename(p).lower()
            if "estimate" in lower_name:
                estimate_pdf = p
            elif "contract" in lower_name:
                contract_pdf = p
                
        if not estimate_pdf:
            self.logger.warning("No 'Estimate' PDF found. Extraction might be incomplete.")
            
        return self._parse_estimate(estimate_pdf, contract_pdf) if estimate_pdf else {}

    def _parse_estimate(self, estimate_pdf_path, contract_pdf_path=None):
        self.logger.info(f"Parsing Estimate PDF: {estimate_pdf_path}")
        result = {
            "client_name": "",
            "project_po": "",
            "line_items": []
        }
        
        debug_md = []
        debug_md.append("# Ingestion Diagnostic Report\n")
        debug_md.append(f"**Estimate File**: `{os.path.basename(estimate_pdf_path)}`\n")
        if contract_pdf_path:
            debug_md.append(f"**Contract File**: `{os.path.basename(contract_pdf_path)}`\n")
        debug_md.append("---\n")
        
        try:
            with pdfplumber.open(estimate_pdf_path) as pdf:
                full_text = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text.append(text)
                
                combined_text = "\n".join(full_text)
                
                # Try to find PO
                po_match = re.search(r"Copy of (\d+)", combined_text)
                if po_match:
                    result["project_po"] = po_match.group(1)
                    
                # Try to extract Name & Address block
                # Usually follows "Estimate Details\n"
                name_match = re.search(r"Estimate Details\n([A-Za-z\s,-]+)\n(\d+\s[A-Za-z\s]+)\n", combined_text)
                if name_match:
                    result["client_name"] = name_match.group(1).strip()
                    
                # Filename Fallback
                if not result["project_po"] or not result["client_name"]:
                    fb_file = contract_pdf_path if contract_pdf_path else estimate_pdf_path
                    if fb_file:
                        base = os.path.basename(fb_file)
                        if not result["project_po"]:
                            po_fb = re.search(r"(\d{5,})", base)
                            if po_fb: result["project_po"] = po_fb.group(1)
                            
                        if not result["client_name"]:
                            name_fb = re.split(r"[-_]", base)[0].strip()
                            if name_fb: result["client_name"] = name_fb

                debug_md.append(f"**Extracted PO**: `{result['project_po']}`\n")
                debug_md.append(f"**Extracted Client**: `{result['client_name']}`\n")
                debug_md.append("---\n## Line Parsing Analysis\n")
                
                # Parse Line Items
                lines = combined_text.split("\n")
                current_room = "Bath 1" # Default starting assumption
                current_item = None
                
                def flush_buffer():
                    nonlocal current_item
                    if not current_item:
                        return
                        
                    desc = "\n".join(current_item["lines"]).strip()
                    lower_desc = desc.lower()
                    qty_val = current_item["qty"]
                    room = current_item["room"]
                    
                    if "demo/install" in lower_desc:
                        debug_md.append(f"- ❌ `Discarded (Demo/Install)`:\n  ```\n  {desc}\n  ```\n")
                    else:
                        is_labor_only = False
                        if "labor" in lower_desc:
                            material_keywords = ["kit", "system", "bundle", "fixture", "faucet", "vanity", "tub", "sink", "countertop", "door", "glass", "hardware", "material", "including"]
                            if not any(kw in lower_desc for kw in material_keywords):
                                is_labor_only = True
                                
                        if is_labor_only:
                            debug_md.append(f"- ❌ `Discarded (Labor only)`:\n  ```\n  {desc}\n  ```\n")
                        else:
                            debug_md.append(f"- ✅ **Accepted (Qty: {qty_val})**:\n  ```\n  {desc}\n  ```\n")
                            result["line_items"].append({
                                "room": room,
                                "raw_description": desc,
                                "qty": qty_val
                            })
                    current_item = None
                
                for i, line in enumerate(lines):
                    lower_line = line.strip().lower()
                    
                    # Ignore structural section dashed lines
                    if "------" in lower_line:
                        continue
                        
                    # Ignore isolated headers
                    if lower_line in ["product", "quantity", "included"] or "product quantity" in lower_line or "product sku description" in lower_line:
                        continue
                        
                    # Rule 1: Room Detectors
                    if lower_line.startswith("bath ") or lower_line.startswith("kitchen"):
                        if len(line.strip()) < 15: # Short explicit header
                            flush_buffer()
                            current_room = line.strip()
                            debug_md.append(f"\n### 🚪 Room Changed to: {current_room}\n")
                            continue
                        
                    # Rule 2: Dynamic Quantity Matcher (e.g. "1 ea", "2ea", "10 ea")
                    qty_match = re.search(r"(?i)(\d+)\s*ea", line)
                    if qty_match:
                        flush_buffer() # Flush the previous item buffer!
                        qty_val = int(qty_match.group(1))
                        
                        # Split by the dynamic match to get the title chunk
                        parts = re.split(r"(?i)\d+\s*ea", line)
                        title_part = parts[0].strip()
                        
                        current_item = {
                            "room": current_room,
                            "qty": qty_val,
                            "lines": [title_part] if title_part else []
                        }
                    else:
                        # Append to the current item's buffer!
                        if current_item is not None:
                            if line.strip():
                                current_item["lines"].append(line.strip())
                        else:
                            # Log unrecognized orphaned lines lightly
                            if len(lower_line) > 10:
                                debug_md.append(f"- [Line {i}] ⏭️ _Orphaned Ignored_: {line}\n")
                
                # Catch the very last item loaded into buffer
                flush_buffer()

                if self.debug_mode:
                    log_dir = os.path.join(self.target_dir, "Debug")
                    os.makedirs(log_dir, exist_ok=True)
                    with open(os.path.join(log_dir, "ingestion_result.md"), "w", encoding='utf-8') as f:
                        f.writelines(debug_md)

                self.logger.debug(f"Extracted {len(result['line_items'])} items.")
                return result
        except Exception as e:
            self.logger.error(f"Error parsing PDF: {e}")
            return result
