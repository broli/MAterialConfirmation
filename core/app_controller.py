import os
import json
from models.matching_engine import MatchService
from models.catalog_loader import CatalogLoader
from models.client_pdf_generator import PDFGenerator
from models.excel_routing_engine import ExcelRoutingEngine
from core.workers import IngestionWorker, OllamaPingWorker
from core.thread_utils import run_in_thread
from PySide6.QtCore import QObject, Signal

class AppController(QObject):
    """
    Central controller that manages the business logic and state for the ERP Command Center.
    It decouples the UI from direct data manipulation and threaded background tasks.
    """
    # Signals emitted back to the UI
    status_updated = Signal(str)
    ollama_status_updated = Signal(bool, str)
    session_loaded = Signal(dict)
    ingestion_finished = Signal(dict)
    ingestion_error = Signal(str)
    generation_finished = Signal(str, str) # type, path
    generation_error = Signal(str, str)    # type, error
    progress_updated = Signal(int, int)
    
    def __init__(self):
        super().__init__()
        self.session_path = ""
        self.session_data = {}
        self.target_pdf_dir = ""
        
        # Load database
        self.db_loader = CatalogLoader(base_path="database")
        self.catalog = self.db_loader.load_all_categories()

        # MatchService — backend entry point for DB-lookup logic.
        self.match_service = MatchService(
            self.catalog,
            debug_mode=False,
            log_dir="logs"
        )
        
        self._threads = []

    def set_debug_mode(self, enabled: bool):
        self.match_service = MatchService(
            self.catalog,
            debug_mode=enabled,
            log_dir="logs"
        )
        msg = "ON — writing to logs/" if enabled else "OFF"
        self.status_updated.emit(f"Debug Logging: {msg}")
        
        # Diagnostic: Force create a file to verify write permissions and directory
        if enabled:
            try:
                os.makedirs("logs", exist_ok=True)
                with open("logs/debug_init.txt", "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().isoformat()}] Debug Mode Enabled\n")
            except Exception as e:
                self.status_updated.emit(f"❌ Log Error: {e}")

    def refresh_catalog(self):
        self.catalog = self.db_loader.load_all_categories()
        self.match_service = MatchService(
            self.catalog,
            debug_mode=self.match_service.debug_mode,
            log_dir="logs"
        )

    def find_product_by_id(self, product_id: str) -> dict | None:
        """Helper to find a specific product in the flat catalog dict."""
        if not product_id:
            return None
        return self.catalog.get(product_id)


    def check_ollama_background(self):
        """Perform a silent ping to warn user if service is offline."""
        worker = OllamaPingWorker(self.match_service)
        worker.signals.result.connect(self._on_ollama_checked)
        run_in_thread(worker, self._threads)

    def _on_ollama_checked(self, result):
        success, err = result
        self.ollama_status_updated.emit(success, err)

    def load_session(self, path: str):
        self.session_path = path
        self.target_pdf_dir = os.path.dirname(path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.session_data = json.load(f)
            self.session_loaded.emit(self.session_data)
            self.status_updated.emit(f"✅ Session loaded: {os.path.basename(path)}")
        except Exception as e:
            self.status_updated.emit(f"❌ Error loading session: {e}")

    def save_session(self, client_name: str, project_po: str):
        if not self.session_path:
            return False
            
        self.session_data["client_name"] = client_name
        self.session_data["project_po"] = project_po
        
        try:
            with open(self.session_path, "w", encoding="utf-8") as f:
                json.dump(self.session_data, f, indent=4)
            self.status_updated.emit(f"💾 Session saved: {os.path.basename(self.session_path)}")
            return True
        except Exception as e:
            self.status_updated.emit(f"❌ Error saving session: {e}")
            return False

    def start_ingestion(self, pdf_path: str):
        self.target_pdf_dir = os.path.dirname(pdf_path)
        self.session_path = os.path.splitext(pdf_path)[0] + ".json"
        
        worker = IngestionWorker(pdf_path, self.match_service.debug_mode, self.match_service)
        
        worker.signals.progress.connect(self.status_updated.emit)
        worker.signals.progress_val.connect(self.progress_updated.emit)
        worker.signals.result.connect(self._on_ingestion_result)
        worker.signals.error.connect(lambda e: self.ingestion_error.emit(str(e[1])))
        
        run_in_thread(worker, self._threads)

    def _on_ingestion_result(self, result):
        if "error" in result:
            self.ingestion_error.emit(result["error"])
        else:
            self.session_data = result["raw_data"]
            self.ingestion_finished.emit(self.session_data)
            self.status_updated.emit(f"✅ Loaded {result.get('count', 0)} items.")

    def get_unmatched_items(self):
        unmatched = []
        for item in self.session_data.get("line_items", []):
            match_meta = item.get("_match", {})
            color_code = match_meta.get("color_code", "red")
            is_ignored = match_meta.get("is_ignored", False)
            confirmed = item.get("confirmed", False)
            
            if color_code != "green" and not is_ignored and not confirmed:
                unmatched.append(item)
        return unmatched

    def toggle_item_confirmation(self, idx: int, match_id: str):
        item = self.session_data["line_items"][idx]
        current_state = item.get("confirmed", False)
        new_state = not current_state
        
        if new_state and not match_id:
            return False, "Cannot confirm an item with no matched ID."
            
        item["confirmed"] = new_state
        if new_state:
            item["matched_id"] = match_id
            self.status_updated.emit(f"✅ Assigned: {match_id}")
        else:
            item.pop("matched_id", None)
            self.status_updated.emit(f"🔄 Unconfirmed: {match_id}")
            
        return True, item

    def reevaluate_unmatched(self):
        """Re-evaluates unconfirmed items against the current catalog asynchronously."""
        if not self.session_data or "line_items" not in self.session_data:
            self.session_loaded.emit(self.session_data)
            return
            
        unconfirmed = [item for item in self.session_data["line_items"] if not item.get("confirmed", False)]
        if not unconfirmed:
            self.session_loaded.emit(self.session_data)
            return
            
        from core.workers import ReevaluateWorker
        worker = ReevaluateWorker(self.session_data["line_items"], self.match_service)
        
        worker.signals.progress.connect(self.status_updated.emit)
        worker.signals.progress_val.connect(self.progress_updated.emit)
        worker.signals.result.connect(self._on_reevaluate_result)
        worker.signals.error.connect(lambda e: self.ingestion_error.emit(str(e[1])))
        
        run_in_thread(worker, self._threads)

    def _on_reevaluate_result(self, changed):
        self.session_loaded.emit(self.session_data)
        if changed:
            self.status_updated.emit("🔄 Re-evaluated unmatched items against database.")

    def resolve_match(self, item):
        return self.match_service.resolve_match(item)

    def prepare_payload(self, client_name: str, project_po: str):
        self.save_session(client_name, project_po)
        payload = {
            "client_info": {
                "name": self.session_data.get("client_name", ""),
                "project": "PO " + self.session_data.get("project_po", "")
            },
            "products": [],
            "custom_pages": self.session_data.get("custom_pages", [])
        }
        
        for item in self.session_data.get("line_items", []):
            if item.get("is_temp"):
                db_item = item.get("temp_product_data", {}).copy()
                db_item["qty"] = item.get("qty", 1)
                db_item["room"] = item.get("room", "General")
                payload["products"].append(db_item)
            elif item.get("confirmed") and item.get("matched_id"):
                db_item = self.catalog.get(item["matched_id"], {}).copy()
                if db_item:
                    if db_item.get("routing_tag", "").strip().upper() == "IGNORE":
                        continue
                        
                    db_item["qty"] = item.get("qty", 1)
                    db_item["room"] = item.get("room", "General")
                    payload["products"].append(db_item)
        return payload

    def generate_pdf(self, client_name: str, project_po: str):
        payload = self.prepare_payload(client_name, project_po)
        if not payload["products"]:
            return False, "No confirmed products to generate PDF."
            
        output_dir = os.path.join(self.target_pdf_dir, "ERP_Automated_Output")
        os.makedirs(output_dir, exist_ok=True)
            
        self.status_updated.emit("⏳ Starting PDF Generation...")
        
        from core.workers import GenerationWorker
        worker = GenerationWorker('pdf', payload, output_dir, self.match_service.debug_mode)
        
        worker.signals.progress.connect(self.status_updated.emit)
        worker.signals.result.connect(lambda path: self.generation_finished.emit('pdf', path))
        worker.signals.error.connect(lambda e: self.generation_error.emit('pdf', str(e[1])))
        
        run_in_thread(worker, self._threads)
        return True, "Started"

    def generate_excel(self, client_name: str, project_po: str):
        payload = self.prepare_payload(client_name, project_po)
        if not payload["products"]:
            return False, "No confirmed products to generate Excel."

        output_dir = os.path.join(self.target_pdf_dir, "ERP_Automated_Output")
        os.makedirs(output_dir, exist_ok=True)
            
        excel_payload = {
            "client_name": payload["client_info"]["name"],
            "project_po": self.session_data.get("project_po", ""),
            "products": payload["products"]
        }
        
        self.status_updated.emit("⏳ Starting Excel Generation...")
        
        from core.workers import GenerationWorker
        worker = GenerationWorker('excel', excel_payload, output_dir, self.match_service.debug_mode)
        
        worker.signals.progress.connect(self.status_updated.emit)
        worker.signals.result.connect(lambda path: self.generation_finished.emit('excel', path))
        worker.signals.error.connect(lambda e: self.generation_error.emit('excel', str(e[1])))
        
        run_in_thread(worker, self._threads)
        return True, "Started"
