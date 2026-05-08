import os
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QHBoxLayout, QTextEdit
from PySide6.QtCore import Qt, QThread, Signal
from models.github_sync_engine import GithubSyncEngine
from models.config_manager import ConfigManager

class SyncWorker(QThread):
    progress = Signal(int, int, str)
    finished = Signal(bool, str)

    def __init__(self, owner, repo, token, local_path, is_publish=False):
        super().__init__()
        self.owner = owner
        self.repo = repo
        self.token = token
        self.local_path = local_path
        self.is_publish = is_publish
        self.engine = GithubSyncEngine(owner, repo, token)

    def run(self):
        try:
            if self.is_publish:
                self.progress.emit(0, 0, "Connecting to GitHub...")
                success, msg = self.engine.publish_changes(self.local_path, progress_callback=self._publish_callback)
                self.finished.emit(success, msg if not success else "Database published successfully!")
            else:
                self.progress.emit(0, 0, "Checking for updates...")
                latest_sha = self.engine.get_latest_commit()
                if not latest_sha:
                    self.finished.emit(False, "Could not connect to repository.")
                    return

                version_file = os.path.join(self.local_path, "version.txt")
                local_sha = ""
                if os.path.exists(version_file):
                    with open(version_file, "r") as f:
                        local_sha = f.read().strip()

                if local_sha == latest_sha:
                    self.finished.emit(True, "Database is already up to date.")
                    return

                if not local_sha:
                    self.progress.emit(0, 0, "Downloading full database (first time setup)...")
                    success = self.engine.download_full_zip(self.local_path, progress_callback=self._download_callback)
                    if success:
                        with open(version_file, "w") as f: f.write(latest_sha)
                        self.finished.emit(True, "Database downloaded successfully!")
                    else:
                        self.finished.emit(False, "Failed to download database.")
                    return

                self.progress.emit(0, 0, "Calculating differences...")
                changes = self.engine.get_changed_files(local_sha, latest_sha)
                
                if changes is None:
                    # Fallback to full download if delta fails
                    self.progress.emit(0, 0, "Delta sync failed. Falling back to full download...")
                    success = self.engine.download_full_zip(self.local_path, progress_callback=self._download_callback)
                    if success:
                        with open(version_file, "w") as f: f.write(latest_sha)
                        self.finished.emit(True, "Database downloaded successfully!")
                    else:
                        self.finished.emit(False, "Failed to download database.")
                    return

                total = len(changes)
                if total == 0:
                    with open(version_file, "w") as f: f.write(latest_sha)
                    self.finished.emit(True, "Database is up to date.")
                    return

                for i, file_data in enumerate(changes):
                    status = file_data.get("status")
                    filename = file_data.get("filename")
                    self.progress.emit(i+1, total, f"Syncing: {filename}")
                    
                    target_path = os.path.join(self.local_path, filename)
                    
                    if status in ["removed"]:
                        if os.path.exists(target_path):
                            os.remove(target_path)
                    else:
                        self.engine.download_file(filename, target_path)

                with open(version_file, "w") as f: f.write(latest_sha)
                self.finished.emit(True, "Database synced successfully!")

        except Exception as e:
            self.finished.emit(False, f"An error occurred: {str(e)}")

    def _publish_callback(self, current, total, text):
        self.progress.emit(current, total, text)

    def _download_callback(self, current, total):
        if current == -1:
            self.progress.emit(0, 0, "Extracting files...")
        else:
            self.progress.emit(current, total, "Downloading zip archive...")


class SyncProgressDialog(QDialog):
    def __init__(self, parent, is_publish=False):
        super().__init__(parent)
        self.setWindowTitle("Publishing Database" if is_publish else "Syncing Database")
        self.resize(600, 400)
        self.is_publish = is_publish
        
        layout = QVBoxLayout(self)
        
        self.lbl_status = QLabel("Initializing...")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.lbl_status)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # Indeterminate initially
        layout.addWidget(self.progress_bar)
        
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background-color: #1e1e1e; color: #dcdcdc; font-family: Consolas, monospace;")
        layout.addWidget(self.log_view)
        
        footer = QHBoxLayout()
        self.btn_close = QPushButton("Close")
        self.btn_close.setEnabled(False)
        self.btn_close.clicked.connect(self.accept)
        footer.addStretch()
        footer.addWidget(self.btn_close)
        layout.addLayout(footer)

    def closeEvent(self, event):
        # Prevent closing while syncing
        if not self.btn_close.isEnabled():
            event.ignore()
        else:
            super().closeEvent(event)

    def start_sync(self, owner, repo, token, local_path):
        self.worker = SyncWorker(owner, repo, token, local_path, self.is_publish)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def append_log(self, message: str):
        self.log_view.append(message)
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def on_progress(self, current, total, text):
        self.lbl_status.setText(text)
        self.append_log(text)
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
        else:
            self.progress_bar.setRange(0, 0)

    def on_finished(self, success, message):
        self.lbl_status.setText(message)
        self.append_log(message)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.btn_close.setEnabled(True)
        
        # Ensure window is visible and on top
        self.show()
        self.raise_()
        self.activateWindow()
        
        if not success:
            self.lbl_status.setStyleSheet("color: red;")
        else:
            self.lbl_status.setStyleSheet("color: #4caf50;")
