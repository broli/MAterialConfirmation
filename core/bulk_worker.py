import os
import json
import time
import glob
import re
from PySide6.QtCore import QThread, Signal, QObject
from models.config_manager import ConfigManager
from models.catalog_loader import CatalogLoader
from models.gemini_service import GeminiClient, QuotaExceededError
from models.product_service import ProductService
from models.contract_ingestion import OneClickIngestor

class BulkWorkerSignals(QObject):
    progress = Signal(str)
    result = Signal(dict)
    error = Signal(tuple)
    finished = Signal()
    status_update = Signal(str)
    countdown_update = Signal(int)
    model_status_update = Signal(str)

class BulkIngestWorker(QObject):
    """
    Background worker that handles the 3-stage bulk ingestion pipeline:
    1. Parse PDFs -> Queue
    2. Heuristic Pre-fill
    3. Gemini API Processor (with retry logic)
    """

    def __init__(self, target_folder_path: str, debug_mode: bool = False, mode: str = "extract"):
        super().__init__()
        self.signals = BulkWorkerSignals()
        self.target_folder_path = target_folder_path
        self.debug_mode = debug_mode
        self.mode = mode
        self.log_file = "logs/bulk_worker_debug.log"
        if self.debug_mode:
            os.makedirs("logs", exist_ok=True)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"\n--- Starting new Bulk Ingestion debug session ({self.mode} mode) at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                
        self.queue_file = os.path.join(target_folder_path, "gemini_queue.json")
        self.is_running = True
        
        self.db_loader = CatalogLoader(base_path="database")
        self.catalog = self.db_loader.load_all_categories() or {}
        
        self.staging_path = "staging_database"
        self.staging_loader = CatalogLoader(base_path=self.staging_path)
        self.staging_catalog = self.staging_loader.load_all_categories() or {}

    def _log_debug(self, msg):
        if not self.debug_mode:
            return
        self.signals.progress.emit(f"[DEBUG] {msg}")
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        except Exception:
            pass

    def stop(self):
        self.is_running = False

    def run(self):
        try:
            self.signals.progress.emit(f"Starting Bulk Ingestion Pipeline ({self.mode} mode)...")
            self.signals.status_update.emit(f"Starting pipeline ({self.mode})...")
            
            if self.mode == "extract":
                # Stage 1: Build Queue from PDFs
                queue = self._build_queue()
                self._save_queue(queue)
                if not queue:
                    self.signals.progress.emit("No new unique items found in PDFs.")
                    self.signals.result.emit({"status": "success", "processed": 0})
                else:
                    self.signals.progress.emit(f"Extraction complete. {len(queue)} items queued in {os.path.basename(self.queue_file)}.")
                    self.signals.result.emit({"status": "success", "processed": len(queue)})
                    
            elif self.mode == "process":
                # Stage 2 & 3: Heuristics and Gemini
                queue = self._load_queue()
                if not queue:
                    self.signals.progress.emit("Queue is empty. Nothing to process.")
                    self.signals.status_update.emit("Queue empty.")
                    self.signals.result.emit({"status": "success", "processed": 0})
                    self.signals.finished.emit()
                    return

                self.signals.progress.emit(f"Queue loaded with {len(queue)} items. Running Heuristics...")
                self.signals.status_update.emit(f"Running Heuristics ({len(queue)} items)...")
                queue = self._run_heuristics(queue)
                self._save_queue(queue)
                
                self.signals.progress.emit(f"Starting Gemini processing for {len(queue)} items...")
                processed_count = self._process_queue_with_gemini()
                
                self.signals.result.emit({"status": "success", "processed": processed_count})
                
        except Exception as e:
            self.signals.error.emit((type(e), e, None))
        finally:
            self.signals.finished.emit()

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

        # Iterate over PDFs in the folder
        pdf_files = glob.glob(os.path.join(self.target_folder_path, "*.pdf"))
        
        if self.debug_mode:
            self._log_debug(f"Looking for PDFs in {self.target_folder_path}")
            self._log_debug(f"Found PDF files: {[os.path.basename(f) for f in pdf_files]}")
            
        for pdf in pdf_files:
            try:
                if self.debug_mode:
                    self._log_debug(f"Extracting {os.path.basename(pdf)}...")
                self.signals.progress.emit(f"Extracting {os.path.basename(pdf)}...")
                
                ingestor = OneClickIngestor(pdf, debug_mode=self.debug_mode)
                data = ingestor.extract_data()
                
                for line_item in data.get("line_items", []):
                    desc = line_item.get("raw_description", "")
                    clean_desc = desc.strip().lower()
                    
                    if clean_desc and clean_desc not in existing_descriptions:
                        # It's a new unique item
                        queue.append({
                            "raw_description": desc,
                            "room": line_item.get("room", "General"),
                            "source_file": os.path.basename(pdf)
                        })
                        existing_descriptions.add(clean_desc)
                        if self.debug_mode:
                            self._log_debug(f"Added to queue: '{desc[:30]}...'")
                    elif self.debug_mode and clean_desc:
                        self._log_debug(f"Skipping duplicate: '{clean_desc[:30]}...'")
            except Exception as e:
                self.signals.progress.emit(f"Warning: Failed to extract from {os.path.basename(pdf)}: {e}")
                if self.debug_mode:
                    self._log_debug(f"Error extracting {os.path.basename(pdf)}: {e}")

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
            gemini = GeminiClient(
                debug_mode=self.debug_mode,
                model_status_callback=self.signals.model_status_update.emit
            )
        except Exception as e:
            self.signals.progress.emit(f"Gemini Init Error: {e}")
            return 0
            
        queue = self._load_queue()
        total_items = len(queue)
        processed_count = 0
        
        while queue and self.is_running:
            item = queue[0]
            desc = item["raw_description"]
            
            self.signals.progress.emit(f"Processing ({processed_count + 1}/{total_items}): {desc[:30]}...")
            self.signals.status_update.emit(f"Processing ({processed_count + 1}/{total_items})")
            
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
                        "dimensions": dict(res.dimensions) if res.dimensions else {}
                    }
                }
                
                category = res.category if res.category and res.category != "UNKNOWN" else item.get("category", "UNKNOWN")
                
                # Sanitize the category string for safe file paths
                clean_category = re.sub(r'[^a-zA-Z0-9_-]', '_', category)
                clean_category = re.sub(r'_+', '_', clean_category).strip('_')
                if not clean_category:
                    clean_category = "UNKNOWN"
                    
                category_filename = f"{clean_category}.yaml"
                
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
                
            except QuotaExceededError as e:
                self.signals.progress.emit(f"🛑 FATAL ERROR: {e}")
                self.signals.status_update.emit("Daily Quota Exhausted! Stopping.")
                self.is_running = False
                break
                
            except Exception as e:
                self.signals.progress.emit(f"API Error. Pausing for 80 seconds... ({e})")
                self.signals.status_update.emit("API Rate Limit - Paused")
                
                # Sleep for 80 seconds checking self.is_running
                for i in range(80):
                    if not self.is_running:
                        break
                    self.signals.countdown_update.emit(80 - i)
                    time.sleep(1)
                
                # Clear countdown when resuming
                self.signals.countdown_update.emit(0)
                
                if not self.is_running:
                    break
                    
        return processed_count
