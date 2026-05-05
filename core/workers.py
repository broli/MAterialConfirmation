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
            if not ready:
                self.signals.error.emit((
                    ConnectionError, 
                    ConnectionError(f"AI service is not responding.\n\n{err}\n\nPlease ensure Ollama is running."), 
                    ""
                ))
                self.signals.finished.emit()
                return

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
