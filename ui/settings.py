import os
import shutil
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QProgressBar, QFrame, QPushButton, QCheckBox, 
                               QComboBox, QLineEdit, QFileDialog, QMessageBox, QScrollArea, QWidget)
from PySide6.QtCore import Qt, QThread, Signal
from models.config_manager import ConfigManager
from models.ollama_utils import OllamaUtils

class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(800, 600)
        self.pending_cover_image = None
        
        main_layout = QVBoxLayout(self)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)
        
        self.loading_lbl = QLabel("Loading settings...")
        self.scroll_layout.addWidget(self.loading_lbl)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.scroll_layout.addWidget(self.progress)
        
        self._load_data()
        self._setup_footer(main_layout)

    def _load_data(self):
        # In a real app this should be a QThread, but for simplicity here we do it fast
        is_installed = OllamaUtils.is_installed()
        is_running = OllamaUtils.is_running()
        models = OllamaUtils.get_models() if is_running else []
        self._on_data_loaded(is_installed, is_running, models)

    def _on_data_loaded(self, is_installed, is_running, models):
        self.loading_lbl.hide()
        self.progress.hide()
        
        role = ConfigManager.get("role") or "user"
        if role == "admin":
            self.build_admin_section()
            self.build_ollama_section(is_installed, is_running, models)
            
        self.build_pdf_section()
        self.scroll_layout.addStretch()

    def build_admin_section(self):
        title_lbl = QLabel("<b>Admin Settings</b>")
        title_lbl.setStyleSheet("font-size: 18px;")
        self.scroll_layout.addWidget(title_lbl)
        
        admin_frame = QFrame()
        admin_layout = QVBoxLayout(admin_frame)
        
        # Gemini API Key
        gemini_layout = QHBoxLayout()
        gemini_layout.addWidget(QLabel("Gemini API Key:"))
        self.entry_gemini = QLineEdit()
        self.entry_gemini.setEchoMode(QLineEdit.EchoMode.Password)
        self.entry_gemini.setText(ConfigManager.get("gemini_api_key") or "")
        gemini_layout.addWidget(self.entry_gemini)
        admin_layout.addLayout(gemini_layout)

        self.scroll_layout.addWidget(admin_frame)

    def build_ollama_section(self, is_installed, is_running, models):
        title_lbl = QLabel("<b>Requirements & Ollama Settings</b>")
        title_lbl.setStyleSheet("font-size: 18px;")
        self.scroll_layout.addWidget(title_lbl)
        
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        
        inst_color = "green" if is_installed else "red"
        run_color = "green" if is_running else "red"
        
        self.lbl_installed = QLabel(f"Installed: {'Yes' if is_installed else 'No'}")
        self.lbl_installed.setStyleSheet(f"color: {inst_color}; font-weight: bold;")
        status_layout.addWidget(self.lbl_installed)
        
        self.lbl_running = QLabel(f"Running: {'Yes' if is_running else 'No'}")
        self.lbl_running.setStyleSheet(f"color: {run_color}; font-weight: bold;")
        status_layout.addWidget(self.lbl_running)
        status_layout.addStretch()
        self.scroll_layout.addWidget(status_frame)
        
        actions_frame = QFrame()
        actions_layout = QVBoxLayout(actions_frame)
        
        if not is_installed:
            btn_download = QPushButton("⬇️ Download Ollama")
            import webbrowser
            btn_download.clicked.connect(lambda: webbrowser.open("https://ollama.com/download"))
            actions_layout.addWidget(btn_download)
        else:
            self.show_window_cb = QCheckBox("Show terminal when starting Ollama")
            self.show_window_cb.setChecked(bool(ConfigManager.get("show_ollama_window")))
            actions_layout.addWidget(self.show_window_cb)
            
            btn_layout = QHBoxLayout()
            self.btn_start = QPushButton("▶️ Start Service")
            self.btn_start.setStyleSheet("background-color: #2e7d32; color: white;")
            self.btn_start.setEnabled(not is_running)
            self.btn_start.clicked.connect(self.start_ollama)
            btn_layout.addWidget(self.btn_start)
            
            self.btn_stop = QPushButton("⏹️ Kill Service")
            self.btn_stop.setStyleSheet("background-color: #c62828; color: white;")
            self.btn_stop.setEnabled(is_running)
            self.btn_stop.clicked.connect(self.stop_ollama)
            btn_layout.addWidget(self.btn_stop)
            btn_layout.addStretch()
            actions_layout.addLayout(btn_layout)
            
            actions_layout.addWidget(QLabel("<b>Model Management</b>"))
            
            self.combo_model = QComboBox()
            if models:
                self.combo_model.addItems(models)
            else:
                self.combo_model.addItem("No models found")
            self.combo_model.setCurrentText(str(ConfigManager.get("llm_model") or ""))
            actions_layout.addWidget(self.combo_model)
            
            pull_layout = QHBoxLayout()
            self.entry_pull = QLineEdit()
            self.entry_pull.setPlaceholderText("e.g. llama3.1")
            pull_layout.addWidget(self.entry_pull)
            self.btn_pull = QPushButton("⬇️ Pull/Update")
            self.btn_pull.clicked.connect(self.pull_model)
            pull_layout.addWidget(self.btn_pull)
            actions_layout.addLayout(pull_layout)
            
            self.btn_delete = QPushButton("🗑️ Delete Selected Model")
            self.btn_delete.setStyleSheet("background-color: #8B0000; color: white;")
            self.btn_delete.clicked.connect(self.delete_model)
            actions_layout.addWidget(self.btn_delete)
            
            self.pull_status_lbl = QLabel("")
            actions_layout.addWidget(self.pull_status_lbl)
            self.pull_progress = QProgressBar()
            self.pull_progress.hide()
            actions_layout.addWidget(self.pull_progress)
            
        self.scroll_layout.addWidget(actions_frame)

    def _setup_footer(self, layout):
        footer = QHBoxLayout()
        
        btn_save = QPushButton("Save Settings")
        btn_save.setMinimumHeight(40)
        btn_save.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; padding: 0 20px;")
        btn_save.clicked.connect(self.save_settings)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setMinimumHeight(40)
        btn_cancel.clicked.connect(self.reject)
        
        footer.addStretch()
        footer.addWidget(btn_save)
        footer.addWidget(btn_cancel)
        layout.addLayout(footer)

    def save_settings(self):
        # Admin Settings
        if hasattr(self, 'entry_gemini'):
            ConfigManager.set("gemini_api_key", self.entry_gemini.text().strip())
        
        # Ollama Settings
        if hasattr(self, 'show_window_cb'):
            ConfigManager.set("show_ollama_window", self.show_window_cb.isChecked())
            
        if hasattr(self, 'combo_model'):
            choice = self.combo_model.currentText()
            if choice and choice != "No models found":
                ConfigManager.set("llm_model", choice)
                
        # PDF Settings
        if self.pending_cover_image:
            ConfigManager.set("cover_image_filename", self.pending_cover_image)
            
        self.accept()

    def refresh_status(self):
        is_running = OllamaUtils.is_running()
        run_color = "green" if is_running else "red"
        self.lbl_running.setText(f"Running: {'Yes' if is_running else 'No'}")
        self.lbl_running.setStyleSheet(f"color: {run_color}; font-weight: bold;")
        
        self.btn_start.setEnabled(not is_running)
        self.btn_stop.setEnabled(is_running)
        
        models = OllamaUtils.get_models() if is_running else []
        self.combo_model.clear()
        if models:
            self.combo_model.addItems(models)
            current = ConfigManager.get("llm_model")
            if current in models:
                self.combo_model.setCurrentText(str(current))
            else:
                self.combo_model.setCurrentIndex(0)
        else:
            self.combo_model.addItem("No models found")

    def start_ollama(self):
        self.btn_start.setEnabled(False)
        OllamaUtils.start_server(show_window=self.show_window_cb.isChecked())
        # Ideally QTimer.singleShot
        from PySide6.QtCore import QTimer
        QTimer.singleShot(2000, self.refresh_status)

    def stop_ollama(self):
        self.btn_stop.setEnabled(False)
        OllamaUtils.stop_server(force_os_kill=True)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(2000, self.refresh_status)

    def delete_model(self):
        model = self.combo_model.currentText()
        if model and model != "No models found":
            reply = QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete {model}?")
            if reply == QMessageBox.StandardButton.Yes:
                if OllamaUtils.delete_model(model):
                    QMessageBox.information(self, "Success", f"Model {model} deleted.")
                    self.refresh_status()
                else:
                    QMessageBox.critical(self, "Error", f"Failed to delete {model}.")

    def pull_model(self):
        model_name = self.entry_pull.text().strip()
        if not model_name:
            QMessageBox.warning(self, "Warning", "Please enter a model name to pull.")
            return
            
        self.btn_pull.setEnabled(False)
        self.pull_progress.show()
        self.pull_status_lbl.setText(f"Starting pull for {model_name}...")
        
        # Simplified: In a real app we need a Worker Thread for pulling models to not freeze UI.
        QMessageBox.information(self, "Info", "Model pull logic would run in a QThread here.")
        self.btn_pull.setEnabled(True)
        self.pull_progress.hide()

    def build_pdf_section(self):
        title_lbl = QLabel("<b>PDF Settings</b>")
        title_lbl.setStyleSheet("font-size: 18px;")
        self.scroll_layout.addWidget(title_lbl)
        
        pdf_frame = QFrame()
        pdf_layout = QHBoxLayout(pdf_frame)
        
        pdf_layout.addWidget(QLabel("Cover Image:"))
        self.lbl_cover_name = QLabel(ConfigManager.get("cover_image_filename"))
        pdf_layout.addWidget(self.lbl_cover_name)
        pdf_layout.addStretch()
        
        btn_pick_cover = QPushButton("Pick New Cover")
        btn_pick_cover.clicked.connect(self.pick_cover_image)
        pdf_layout.addWidget(btn_pick_cover)
        
        self.scroll_layout.addWidget(pdf_frame)

    def pick_cover_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Cover Image", "", "Image Files (*.png *.jpg *.jpeg)")
        if file_path:
            filename = os.path.basename(file_path)
            dest_path = os.path.join("database", "assets", filename)
            
            try:
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                if os.path.abspath(file_path) != os.path.abspath(dest_path):
                    shutil.copy2(file_path, dest_path)
                    
                self.pending_cover_image = filename
                self.lbl_cover_name.setText(f"{filename} (Pending Save)")
                self.lbl_cover_name.setStyleSheet("color: #ffa726; font-weight: bold;")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import image: {e}")
