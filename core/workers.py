from PySide6.QtCore import QObject, Signal, QThread
import traceback
import os
from models.github_sync_engine import GithubSyncEngine

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
    progress_val = Signal(int, int)


class UpdateChecker(QObject):
    def __init__(self, owner, repo, token, local_path):
        super().__init__()
        self.owner = owner
        self.repo = repo
        self.token = token
        self.local_path = local_path
        self.signals = WorkerSignals()
        
    def run(self):
        try:
            engine = GithubSyncEngine(self.owner, self.repo, self.token)
            latest_sha = engine.get_latest_commit()
            if not latest_sha:
                self.signals.result.emit(False)
                return
                
            version_file = os.path.join(self.local_path, "version.txt")
            local_sha = ""
            if os.path.exists(version_file):
                with open(version_file, "r") as f:
                    local_sha = f.read().strip()
                    
            self.signals.result.emit(local_sha != latest_sha)
        except Exception as e:
            self.signals.error.emit((type(e), e, traceback.format_exc()))
            self.signals.result.emit(False)
        finally:
            self.signals.finished.emit()


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

    def _progress_val_callback(self, current: int, total: int):
        self.signals.progress_val.emit(current, total)

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
                        ConnectionError(f"AI service is not configured or responding.\n\n{err}\n\nPlease ensure you have entered a valid Gemini API Key in Settings."), 
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
                progress_callback=self._progress_val_callback,
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

    def _progress_val_callback(self, current: int, total: int):
        self.signals.progress_val.emit(current, total)

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
                progress_callback=self._progress_val_callback,
                status_callback=self._progress_callback
            )

            self.signals.progress.emit("✅ Re-evaluation complete.")
            self.signals.result.emit(True)
        except Exception as e:
            self.signals.error.emit((type(e), e, traceback.format_exc()))
        finally:
            self.signals.finished.emit()


class SyncWorker(QObject):
    """
    Worker for syncing the database with GitHub.
    Can either be a 'download' (sync) or 'upload' (publish).
    """
    def __init__(self, owner, repo, token, local_path, is_publish=False):
        super().__init__()
        self.owner = owner
        self.repo = repo
        self.token = token
        self.local_path = local_path
        self.is_publish = is_publish
        self.signals = WorkerSignals()

    def _progress_callback(self, current, total, msg=None):
        if msg:
            self.signals.progress.emit(msg)
        if total > 0:
            self.signals.progress_val.emit(current, total)

    def run(self):
        try:
            engine = GithubSyncEngine(self.owner, self.repo, self.token)
            
            if self.is_publish:
                self.signals.progress.emit("🚀 Preparing to publish changes...")
                success, result = engine.publish_changes(
                    self.local_path, 
                    progress_callback=lambda c, t, m: self._progress_callback(c, t, m)
                )
                if success:
                    self.signals.result.emit((True, f"Successfully published! New SHA: {result[:7]}"))
                else:
                    self.signals.result.emit((False, f"Publish failed: {result}"))
            else:
                self.signals.progress.emit("🔄 Checking for updates...")
                self.signals.progress.emit("📥 Downloading latest database...")
                success = engine.download_full_zip(
                    self.local_path,
                    progress_callback=lambda c, t: self._progress_callback(c, t)
                )
                if success:
                    # Update version.txt
                    latest_sha = engine.get_latest_commit()
                    if latest_sha:
                        version_file = os.path.join(self.local_path, "version.txt")
                        with open(version_file, "w") as f:
                            f.write(latest_sha)
                    self.signals.result.emit((True, "Database synchronized successfully."))
                else:
                    self.signals.result.emit((False, "Failed to download database update."))
                    
        except Exception as e:
            self.signals.error.emit((type(e), e, traceback.format_exc()))
            self.signals.result.emit((False, str(e)))
        finally:
            self.signals.finished.emit()

