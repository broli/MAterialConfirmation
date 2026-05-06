import os
import json
from models.matching_engine import MatchService
from models.catalog_loader import CatalogLoader
from models.client_pdf_generator import PDFGenerator
from models.excel_routing_engine import ExcelRoutingEngine
from core.workers import IngestionWorker, OllamaPingWorker
from PySide6.QtCore import QThread, QObject, Signal

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
        thread = QThread()
        worker = OllamaPingWorker(self.match_service)
        worker.moveToThread(thread)
        thread._worker = worker  # Prevent garbage collection
        
        thread.started.connect(worker.run)
        worker.signals.result.connect(self._on_ollama_checked)
        worker.signals.finished.connect(thread.quit)
        worker.signals.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        
        self._threads.append(thread)
        thread.start()

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
        
        thread = QThread()
        worker = IngestionWorker(pdf_path, self.match_service.debug_mode, self.match_service)
        worker.moveToThread(thread)
        thread._worker = worker  # Prevent garbage collection
        
        thread.started.connect(worker.run)
        worker.signals.progress.connect(self.status_updated.emit)
        worker.signals.result.connect(self._on_ingestion_result)
        worker.signals.error.connect(lambda e: self.ingestion_error.emit(str(e[1])))
        worker.signals.finished.connect(thread.quit)
        worker.signals.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        
        self._threads.append(thread)
        thread.start()

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

    def resolve_match(self, item):
        return self.match_service.resolve_match(item)

    def prepare_payload(self, client_name: str, project_po: str):
        self.save_session(client_name, project_po)
        payload = {
            "client_info": {
                "name": self.session_data.get("client_name", ""),
                "project": "PO " + self.session_data.get("project_po", "")
            },
            "products": []
        }
        
        for item in self.session_data.get("line_items", []):
            if item.get("confirmed") and item.get("matched_id"):
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
            
        generator = PDFGenerator(output_path=output_dir, debug_mode=self.match_service.debug_mode)
        out_file = generator.create_pdf(payload)
        self.status_updated.emit(f"✅ PDF saved to: {os.path.basename(out_file)}")
        return True, out_file

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
        generator = ExcelRoutingEngine(output_dir=output_dir, debug_mode=self.match_service.debug_mode)
        out_file = generator.generate_excel(excel_payload)
        if out_file:
            self.status_updated.emit(f"✅ Excel saved to: {os.path.basename(out_file)}")
            return True, out_file
        else:
            return False, "Missing Excel Template file in /database/templates dir."
