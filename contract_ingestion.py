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
        logger.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)
        if not logger.handlers:
            os.makedirs("logs", exist_ok=True)
            fh = logging.FileHandler("logs/ingestion_debug.log")
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        return logger

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
            
        return self._parse_estimate(estimate_pdf) if estimate_pdf else {}

    def _parse_estimate(self, pdf_path):
        self.logger.info(f"Parsing Estimate PDF: {pdf_path}")
        result = {
            "client_name": "",
            "project_po": "",
            "line_items": []
        }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
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
                    
                # Parse Line Items
                lines = combined_text.split("\n")
                in_table = False
                for i, line in enumerate(lines):
                    # We found the header row
                    if "Product SKU Description Qty" in line:
                        in_table = True
                        continue
                    
                    if in_table:
                        # Stop if we hit a dash separator or a subheader 
                        if "------" in line or line.startswith("Bath 2"):
                            break
                            
                        # Look for lines that look like specific products in standard format
                        # Simplistic extraction checking for 1 ea 
                        if "1 ea" in line:
                            parts = line.split("1 ea")
                            desc = parts[0].strip()
                            result["line_items"].append({
                                "raw_description": desc,
                                "qty": 1
                            })

                self.logger.debug(f"Extracted {len(result['line_items'])} items.")
                return result
        except Exception as e:
            self.logger.error(f"Error parsing PDF: {e}")
            return result
