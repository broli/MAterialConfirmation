from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QLabel, QPushButton, QHBoxLayout, QProgressBar
from PySide6.QtCore import Qt

class ProgressDialog(QDialog):
    """
    Unified dialog for tracking the progress of long-running background tasks.
    Supports a determinate progress bar, text log, and status updates.
    """
    def __init__(self, parent=None, title="Progress", show_abort=True):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.model_status_label = QLabel("")
        self.model_status_label.setStyleSheet("color: #4caf50; font-weight: bold; font-style: italic; font-size: 12px;")
        self.model_status_label.hide()
        layout.addWidget(self.model_status_label)
        
        self.countdown_label = QLabel("")
        self.countdown_label.setStyleSheet("color: #ff9800; font-weight: bold;")
        self.countdown_label.hide()
        layout.addWidget(self.countdown_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # Indeterminate initially
        layout.addWidget(self.progress_bar)
        
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background-color: #1e1e1e; color: #dcdcdc; font-family: Consolas, monospace;")
        layout.addWidget(self.log_view)
        
        footer = QHBoxLayout()
        footer.addStretch()
        
        self.btn_abort = QPushButton("🛑 Abort Process")
        self.btn_abort.setStyleSheet("background-color: #d32f2f; color: white;")
        self.btn_abort.clicked.connect(self.reject)
        
        if show_abort:
            footer.addWidget(self.btn_abort)
        else:
            self.btn_abort.hide()
            
        self.btn_close = QPushButton("Close")
        self.btn_close.setEnabled(False)
        self.btn_close.clicked.connect(self.accept)
        footer.addWidget(self.btn_close)
        
        layout.addLayout(footer)

    def closeEvent(self, event):
        # Prevent closing manually if task is still running and no abort button is present
        if not self.btn_close.isEnabled() and self.btn_abort.isHidden():
            event.ignore()
        else:
            super().closeEvent(event)

    def append_log(self, message: str):
        self.log_view.append(message)
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def update_status(self, text: str):
        self.status_label.setText(text)
        
    def update_model_status(self, text: str):
        if text:
            self.model_status_label.setText(f"🤖 {text}")
            self.model_status_label.show()
        else:
            self.model_status_label.hide()
        
    def update_countdown(self, seconds: int):
        if seconds > 0:
            self.countdown_label.setText(f"⏳ Retrying in {seconds}s...")
            self.countdown_label.show()
        else:
            self.countdown_label.hide()

    def update_progress(self, current: int, total: int):
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
        else:
            self.progress_bar.setRange(0, 0)

    def set_finished(self):
        self.btn_close.setEnabled(True)
        self.btn_abort.hide()
        # Do not override the status label here. Let the worker provide the final status text.
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
