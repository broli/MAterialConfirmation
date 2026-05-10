import os
import json
import time
import glob
from PySide6.QtCore import QThread, Signal, QObject
from models.config_manager import ConfigManager
from models.catalog_loader import CatalogLoader
from models.gemini_service import GeminiClient
from models.product_service import ProductService

class BulkIngestWorker(QObject):
    """
    Background worker that handles the 3-stage bulk ingestion pipeline:
    1. Parse PDFs -> Queue
    2. Heuristic Pre-fill
    3. Gemini API Processor (with retry logic)
    """
    progress = Signal(str)
    result = Signal(dict)
    error = Signal(tuple)
    finished = Signal()

    def __init__(self, pdf_folder_path: str, debug_mode: bool = False):
        super().__init__()
        self.pdf_folder_path = pdf_folder_path
        self.debug_mode = debug_mode
        self.queue_file = os.path.join(pdf_folder_path, "gemini_queue.json")
        self.is_running = True
        
        self.db_loader = CatalogLoader(base_path="database")
        self.catalog = self.db_loader.load_all_categories() or {}
        
        self.staging_path = "staging_database"
        self.staging_loader = CatalogLoader(base_path=self.staging_path)
        self.staging_catalog = self.staging_loader.load_all_categories() or {}

    def stop(self):
        self.is_running = False

    def run(self):
        try:
            self.progress.emit("Starting Bulk Ingestion Pipeline...")
            
            # Stage 1 & 2: Build Queue and run Heuristics
            queue = self._build_queue()
            if not queue:
                self.progress.emit("No new unique items found in PDFs.")
                self.result.emit({"status": "success", "processed": 0})
                self.finished.emit()
                return

            self.progress.emit(f"Queue built with {len(queue)} items. Running Heuristics...")
            queue = self._run_heuristics(queue)
            self._save_queue(queue)
            
            # Stage 3: Process Queue with Gemini
            self.progress.emit(f"Starting Gemini processing for {len(queue)} items...")
            processed_count = self._process_queue_with_gemini()
            
            self.result.emit({"status": "success", "processed": processed_count})
        except Exception as e:
            self.error.emit((type(e), e, None))
        finally:
            self.finished.emit()

    def _save_queue(self, queue):
        with open(self.queue_file, "w", encoding="utf-8") as f:
            json.dump(queue, f, indent=4)

    def _load_queue(self):
        if os.path.exists(self.queue_file):
            with open(self.queue_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _build_queue(self):
        """
        Scans all PDFs in the folder (mocked for simplicity, in reality calls PDF parser).
        Since we don't have the actual PDF parser logic here, we'll assume a session JSON 
        exists for each PDF or we parse them. We'll find all unmatched items across all 
        session JSON files in the folder.
        """
        queue = self._load_queue()
        existing_descriptions = {item.get("raw_description", "").strip().lower() for item in queue}
        
        # Also add all existing production & staging descriptions to prevent duplicates
        for item in (self.catalog or {}).values():
            desc = item.get("oneclick_description", "").strip().lower()
            if desc: existing_descriptions.add(desc)
            
        for item in (self.staging_catalog or {}).values():
            desc = item.get("oneclick_description", "").strip().lower()
            if desc: existing_descriptions.add(desc)

        # Iterate over session JSONs in the folder (as the PDF extractor usually outputs them)
        json_files = glob.glob(os.path.join(self.pdf_folder_path, "*.json"))
        
        if self.debug_mode:
            self.progress.emit(f"[DEBUG] Looking for JSONs in {self.pdf_folder_path}")
            self.progress.emit(f"[DEBUG] Found JSON files: {[os.path.basename(f) for f in json_files]}")
            
        for jf in json_files:
            if os.path.basename(jf) == "gemini_queue.json":
                continue
                
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                for line_item in data.get("line_items", []):
                    desc = line_item.get("raw_description", "")
                    clean_desc = desc.strip().lower()
                    
                    if clean_desc and clean_desc not in existing_descriptions:
                        # It's a new unique item
                        queue.append({
                            "raw_description": desc,
                            "room": line_item.get("room", "General"),
                            "source_file": os.path.basename(jf)
                        })
                        existing_descriptions.add(clean_desc)
                    elif self.debug_mode and clean_desc:
                        self.progress.emit(f"[DEBUG] Skipping duplicate: '{clean_desc[:30]}...'")
            except Exception as e:
                self.progress.emit(f"Warning: Failed to read {jf}: {e}")

        return queue

    def _run_heuristics(self, queue):
        """
        Scans production database to build dictionary of brands/providers and guesses them.
        """
        known_brands = set()
        for item in (self.catalog or {}).values():
            b = item.get("brand", "").strip()
            if b: known_brands.add(b)

        for q_item in queue:
            # Only apply if not already set
            if "brand" not in q_item:
                desc_lower = q_item["raw_description"].lower()
                for kb in known_brands:
                    if kb.lower() in desc_lower:
                        q_item["brand"] = kb
                        break # First match wins for simple heuristic
            
            # Ensure "UNKNOWN" fallback for missing critical fields before LLM gets it
            if "category" not in q_item: q_item["category"] = "UNKNOWN"
            if "brand" not in q_item: q_item["brand"] = "UNKNOWN"
            if "finish" not in q_item: q_item["finish"] = "UNKNOWN"
            
        return queue

    def _process_queue_with_gemini(self):
        try:
            gemini = GeminiClient(debug_mode=self.debug_mode)
        except Exception as e:
            self.progress.emit(f"Gemini Init Error: {e}")
            return 0
            
        queue = self._load_queue()
        total_items = len(queue)
        processed_count = 0
        
        while queue and self.is_running:
            item = queue[0]
            desc = item["raw_description"]
            
            self.progress.emit(f"Processing ({processed_count + 1}/{total_items}): {desc[:30]}...")
            
            try:
                # Call Gemini
                res = gemini.extract_product_fields(desc)
                
                # Merge heuristic data with LLM data (heuristic wins if LLM hallucinated, but LLM fills UNKNOWNs)
                final_data = {
                    "sku": "UNKNOWN",
                    "brand": res.brand if res.brand and res.brand != "UNKNOWN" else item.get("brand", "UNKNOWN"),
                    "finish": res.finish if res.finish else item.get("finish", "UNKNOWN"),
                    "routing_tag": "GENERAL",
                    "oneclick_description": desc,
                    "printable": {
                        "description": res.base_item or desc,
                        "finish": res.finish or "",
                        "dimensions": str(res.dimensions) if res.dimensions else ""
                    }
                }
                
                category = res.category if res.category and res.category != "UNKNOWN" else item.get("category", "UNKNOWN")
                category_filename = f"{category.replace(' ', '_')}.yaml"
                
                # Save to Staging
                import uuid
                final_data["id"] = f"STG-{uuid.uuid4().hex[:8].upper()}"
                
                ProductService.upsert_to_yaml(
                    final_data, 
                    category_filename, 
                    os.path.join(self.staging_path, "categories"), 
                    os.path.join(self.staging_path, "assets")
                )
                
                # Remove from queue and save
                queue.pop(0)
                self._save_queue(queue)
                processed_count += 1
                
                # Small delay to be polite to API
                time.sleep(1)
                
            except Exception as e:
                self.progress.emit(f"API Error. Pausing for 5 minutes... ({e})")
                
                # Sleep for 5 minutes checking self.is_running
                for _ in range(300):
                    if not self.is_running:
                        break
                    time.sleep(1)
                
                if not self.is_running:
                    break
                    
        return processed_count
