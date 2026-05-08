from PySide6.QtCore import QObject, Signal, QThread
import traceback

class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    Supported signals are:
    
    finished: No data
    error: tuple (exctype, value, traceback.format_exc() )
    result: object data returned from processing
    progress: string message indicating current state
    status_color: string hex color code or name for UI elements
    """
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(str)
    status_color = Signal(str)


class OllamaPingWorker(QObject):
    """
    Worker for checking if Ollama is running in the background without blocking the UI.
    """
    def __init__(self, match_service):
        super().__init__()
        self.match_service = match_service
        self.signals = WorkerSignals()

    def run(self):
        try:
            success, err = self.match_service.check_ollama_ready()
            self.signals.result.emit((success, err))
        except Exception as e:
            self.signals.error.emit((type(e), e, traceback.format_exc()))
        finally:
            self.signals.finished.emit()


class IngestionWorker(QObject):
    """
    Worker for executing PDF ingestion and LLM enrichment in the background.
    Emits progress strings to update the UI status bar.
    """
    def __init__(self, pdf_path, debug_mode, match_service):
        super().__init__()
        self.pdf_path = pdf_path
        self.debug_mode = debug_mode
        self.match_service = match_service
        self.signals = WorkerSignals()

    def _progress_callback(self, msg: str):
        # We pass this callback down into the service to receive progress updates
        self.signals.progress.emit(msg)

    def run(self):
        try:
            # Step 1: Check Ollama connection
            self.signals.progress.emit("🔍 Checking AI service...")
            ready, err = self.match_service.check_ollama_ready()
            
            from models.config_manager import ConfigManager
            role = ConfigManager.get("role") or "user"
            
            if not ready:
                if role == "admin":
                    self.signals.error.emit((
                        ConnectionError, 
                        ConnectionError(f"AI service is not responding.\n\n{err}\n\nPlease ensure Ollama is running."), 
                        ""
                    ))
                    self.signals.finished.emit()
                    return
                else:
                    self.signals.progress.emit("⚠️ AI service offline. Using strict database matching...")

            # Step 2: Extract data from PDF
            self.signals.progress.emit("📖 Extracting PDF...")
            # We import here to avoid circular imports or UI dependencies where possible
            from models.contract_ingestion import OneClickIngestor
            ingestor = OneClickIngestor(self.pdf_path, self.debug_mode)
            raw_data = ingestor.extract_data()

            if not raw_data.get("line_items"):
                self.signals.result.emit({"error": "no_items", "raw_data": raw_data})
                self.signals.finished.emit()
                return

            n = len(raw_data["line_items"])
            self.signals.progress.emit(f"✅ PDF Extracted! Found {n} items. Starting AI matching...")

            # Step 3: Enrich with LLM
            self.match_service.enrich_items(
                raw_data["line_items"],
                status_callback=self._progress_callback
            )

            # Step 4: Emit final structured data back to UI
            self.signals.progress.emit(f"🎉 Process Complete! {n} items processed.")
            self.signals.result.emit({"success": True, "raw_data": raw_data, "count": n})

        except Exception as e:
            self.signals.error.emit((type(e), e, traceback.format_exc()))
        finally:
            self.signals.finished.emit()


class GenerationWorker(QObject):
    """
    Worker for generating PDF or Excel files in the background.
    """
    def __init__(self, task_type, payload, output_dir, debug_mode):
        super().__init__()
        self.task_type = task_type # 'pdf' or 'excel'
        self.payload = payload
        self.output_dir = output_dir
        self.debug_mode = debug_mode
        self.signals = WorkerSignals()

    def run(self):
        try:
            if self.task_type == 'pdf':
                from models.client_pdf_generator import PDFGenerator
                self.signals.progress.emit("🎨 Creating Client PDF...")
                generator = PDFGenerator(output_path=self.output_dir, debug_mode=self.debug_mode)
                out_file = generator.create_pdf(self.payload)
                self.signals.result.emit(out_file)
            
            elif self.task_type == 'excel':
                from models.excel_routing_engine import ExcelRoutingEngine
                self.signals.progress.emit("📊 Creating Material Cart Excel...")
                generator = ExcelRoutingEngine(output_dir=self.output_dir, debug_mode=self.debug_mode)
                out_file = generator.generate_excel(self.payload)
                if out_file:
                    self.signals.result.emit(out_file)
                else:
                    self.signals.error.emit((FileNotFoundError, FileNotFoundError("Excel template missing"), ""))
        except Exception as e:
            self.signals.error.emit((type(e), e, traceback.format_exc()))
        finally:
            self.signals.finished.emit()

class ReevaluateWorker(QObject):
    """
    Worker for re-evaluating unmatched items in the background.
    """
    def __init__(self, line_items, match_service):
        super().__init__()
        self.line_items = line_items
        self.match_service = match_service
        self.signals = WorkerSignals()

    def _progress_callback(self, msg: str):
        self.signals.progress.emit(msg)

    def run(self):
        try:
            items_to_eval = [item for item in self.line_items if not item.get("confirmed", False)]
            if not items_to_eval:
                self.signals.progress.emit("✅ Re-evaluation complete.")
                self.signals.result.emit(False)
                return

            for item in items_to_eval:
                if "_match" in item:
                    del item["_match"]

            self.match_service.enrich_items(
                items_to_eval,
                status_callback=self._progress_callback
            )

            self.signals.progress.emit("✅ Re-evaluation complete.")
            self.signals.result.emit(True)
        except Exception as e:
            self.signals.error.emit((type(e), e, traceback.format_exc()))
        finally:
            self.signals.finished.emit()

