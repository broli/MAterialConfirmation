import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QPushButton, QLineEdit, QCheckBox, 
                               QScrollArea, QFrame, QFileDialog, QMessageBox, QDialog, QSizePolicy, QSpacerItem, QProgressBar)
from PySide6.QtCore import Qt, QSize, QThread, Signal
from PySide6.QtGui import QIcon

from ui.custom_pages_dialog import CustomPagesDialog
from models.config_manager import ConfigManager
from ui.settings import SettingsWindow
from ui.database_manager import DatabaseManager
from ui.batch_pdf import BatchPdfIngestWindow
from ui.ingestion_progress import IngestionProgressDialog
from ui.product_detail import ProductDetailDialog
from ui.components.product_form import ProductFormWidget
from ui.sync_progress_dialog import SyncProgressDialog
from models.github_sync_engine import GithubSyncEngine

class UpdateChecker(QThread):
    finished = Signal(bool) # True if update available

    def __init__(self, owner, repo, token, local_path):
        super().__init__()
        self.owner = owner
        self.repo = repo
        self.token = token
        self.local_path = local_path
        
    def run(self):
        try:
            engine = GithubSyncEngine(self.owner, self.repo, self.token)
            latest_sha = engine.get_latest_commit()
            if not latest_sha:
                self.finished.emit(False)
                return
                
            version_file = os.path.join(self.local_path, "version.txt")
            local_sha = ""
            if os.path.exists(version_file):
                with open(version_file, "r") as f:
                    local_sha = f.read().strip()
                    
            self.finished.emit(local_sha != latest_sha)
        except Exception:
            self.finished.emit(False)

class TempItemEditDialog(QDialog):
    def __init__(self, parent, categories_path="database/categories", item_data=None):
        super().__init__(parent)
        self.categories_path = categories_path
        self.item_data = item_data or {}
        
        self.setWindowTitle("Add Temporary Item" if not item_data else "Edit Temporary Item")
        self.resize(600, 750)
        
        layout = QVBoxLayout(self)
        
        # Temp Item specific fields
        top_group = QFrame()
        top_layout = QHBoxLayout(top_group)
        
        top_layout.addWidget(QLabel("Room:"))
        self.room_entry = QLineEdit(self.item_data.get("room", "General"))
        top_layout.addWidget(self.room_entry)
        
        top_layout.addWidget(QLabel("Qty:"))
        self.qty_entry = QLineEdit(str(self.item_data.get("qty", 1)))
        self.qty_entry.setMaximumWidth(60)
        top_layout.addWidget(self.qty_entry)
        
        layout.addWidget(top_group)
        
        # Product Form
        self.form = ProductFormWidget(self, categories_path=self.categories_path)
        
        # Map item_data to product form
        prod_data = self.item_data.get("temp_product_data", {})
        if not prod_data and not self.item_data:
            # Default values for new temp item
            prod_data = {
                "id": "TEMP",
                "sku": "TEMP",
                "brand": "Custom",
                "routing_tag": "GENERAL",
            }
        self.form.load_data(prod_data, prod_data.get("category_file", ""))
        layout.addWidget(self.form)
        
        # Footer
        footer = QHBoxLayout()
        btn_save = QPushButton("Save")
        btn_save.setStyleSheet("background-color: #2e7d32; color: white;")
        btn_save.clicked.connect(self.save)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        footer.addStretch()
        footer.addWidget(btn_save)
        footer.addWidget(btn_cancel)
        layout.addLayout(footer)

    def save(self):
        prod_data, cat_file = self.form.get_data()
        
        qty_str = self.qty_entry.text().strip()
        try:
            qty = int(qty_str) if qty_str else 1
        except ValueError:
            qty = 1
            
        self.result_data = {
            "room": self.room_entry.text().strip() or "General",
            "qty": qty,
            "raw_description": prod_data.get("oneclick_description", "Temporary Item"),
            "temp_product_data": prod_data,
            "confirmed": True,
            "is_temp": True,
            "_match": {
                "match_id": prod_data.get("id", "TEMP"),
                "confidence": 100,
                "color_hex": "#000000"
            }
        }
        self.accept()

from PySide6.QtCore import QTimer

class ClickableRow(QFrame):
    def __init__(self, index, callback):
        super().__init__()
        self.index = index
        self.callback = callback
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            QTimer.singleShot(0, lambda: self.callback(self.index))

class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.ingestion_dialog = None
        
        self.setWindowTitle("PKB ERP Command Center v3.1 (Qt)")
        self.setMinimumSize(1200, 800)
        
        # Load window geometry from config
        width = ConfigManager.get("main_window_width")
        height = ConfigManager.get("main_window_height")
        x = ConfigManager.get("main_window_x")
        y = ConfigManager.get("main_window_y")
        is_maximized = ConfigManager.get("main_window_maximized")
        
        if width and height:
            self.resize(width, height)
            if x is not None and y is not None:
                self.move(x, y)
        
        if is_maximized:
            self.setWindowState(Qt.WindowState.WindowMaximized)
        
        # Central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        self._setup_header()
        self._setup_workspace()
        self._setup_footer()
        self._setup_status_bar()
        
        # Connect to controller signals
        self.controller.status_updated.connect(self.update_status)
        self.controller.ollama_status_updated.connect(self._on_ollama_status)
        self.controller.session_loaded.connect(self.populate_ui)
        self.controller.ingestion_finished.connect(self.populate_ui)
        self.controller.ingestion_error.connect(self.show_error)
        self.controller.generation_finished.connect(self._on_generation_finished)
        self.controller.generation_error.connect(self._on_generation_error)
        
        # Start Ollama check
        if ConfigManager.get("role") == "admin":
            self.controller.check_ollama_background()
        
        # Start Update Check
        self.check_for_updates()

    def check_for_updates(self):
        owner = ConfigManager.get("github_owner") or "YOUR_COMPANY_GITHUB_USERNAME"
        repo = ConfigManager.get("github_repo") or "material-confirmation-db"
        token = ConfigManager.get("github_token")
        local_path = self.controller.db_loader.base_path
        
        self.update_checker = UpdateChecker(owner, repo, token, local_path)
        self.update_checker.finished.connect(self._on_update_check_done)
        self.update_checker.start()
        
    def _on_update_check_done(self, update_available):
        if update_available:
            self.open_sync_dialog(is_publish=False)

    def _setup_header(self):
        header_frame = QFrame()
        layout = QHBoxLayout(header_frame)
        
        title_lbl = QLabel("Command Center")
        title_lbl.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title_lbl)
        
        self.btn_load_dir = QPushButton("📁 Pick Agreement")
        self.btn_load_dir.clicked.connect(self.load_directory)
        layout.addWidget(self.btn_load_dir)
        
        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        self.debug_var = QCheckBox("Enable Developer Logging")
        self.debug_var.stateChanged.connect(self.toggle_debug)
        layout.addWidget(self.debug_var)
        
        role = ConfigManager.get("role") or "user"
        
        if role == "admin":
            self.btn_manage_db = QPushButton("⚙️ Manage Database")
            self.btn_manage_db.setStyleSheet("background-color: #1565c0; color: white;")
            self.btn_manage_db.clicked.connect(self.open_database_manager)
            layout.addWidget(self.btn_manage_db)
            
            self.btn_publish = QPushButton("🚀 Publish Database")
            self.btn_publish.setStyleSheet("background-color: #d32f2f; color: white;")
            self.btn_publish.clicked.connect(lambda: self.open_sync_dialog(is_publish=True))
            layout.addWidget(self.btn_publish)
        else:
            self.btn_sync = QPushButton("🔄 Sync Database")
            self.btn_sync.setStyleSheet("background-color: #1976d2; color: white;")
            self.btn_sync.clicked.connect(lambda: self.open_sync_dialog(is_publish=False))
            layout.addWidget(self.btn_sync)
            
        self.btn_settings = QPushButton("⚙️ Settings")
        self.btn_settings.clicked.connect(self.open_settings)
        layout.addWidget(self.btn_settings)
        
        self.main_layout.addWidget(header_frame)

    def _setup_workspace(self):
        workspace = QFrame()
        w_layout = QVBoxLayout(workspace)
        
        # Top Info
        info_frame = QFrame()
        i_layout = QHBoxLayout(info_frame)
        i_layout.setContentsMargins(0, 0, 0, 0)
        
        i_layout.addWidget(QLabel("Client Name:"))
        self.entry_client = QLineEdit()
        i_layout.addWidget(self.entry_client)
        
        i_layout.addWidget(QLabel("Project PO:"))
        self.entry_po = QLineEdit()
        i_layout.addWidget(self.entry_po)
        
        i_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        self.hide_ignored_var = QCheckBox("Hide Ignored Items")
        self.hide_ignored_var.setChecked(True)
        self.hide_ignored_var.stateChanged.connect(lambda: self.populate_ui())
        i_layout.addWidget(self.hide_ignored_var)
        
        w_layout.addWidget(info_frame)
        
        # Unified Workspace Area
        workspace_frame = QFrame()
        workspace_vbox = QVBoxLayout(workspace_frame)
        
        # Headers Row
        headers_layout = QHBoxLayout()
        lbl_left = QLabel("<b>Extracted Contract Lines</b>")
        lbl_right = QLabel("<b>Suggested DB Match (Action Required)</b>")
        headers_layout.addWidget(lbl_left, 1)
        headers_layout.addWidget(lbl_right, 1)
        workspace_vbox.addLayout(headers_layout)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.workspace_content = QWidget()
        self.workspace_grid = QGridLayout(self.workspace_content)
        self.workspace_grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.workspace_grid.setColumnStretch(0, 1)
        self.workspace_grid.setColumnStretch(1, 1)
        self.scroll_area.setWidget(self.workspace_content)
        
        workspace_vbox.addWidget(self.scroll_area)
        w_layout.addWidget(workspace_frame, 1)
        
        self.main_layout.addWidget(workspace, 1)

    def _setup_footer(self):
        footer_frame = QFrame()
        layout = QHBoxLayout(footer_frame)
        
        self.btn_save_session = QPushButton("💾 Save Session")
        self.btn_save_session.clicked.connect(self.save_session)
        layout.addWidget(self.btn_save_session)
        
        self.btn_add_temp = QPushButton("➕ Add Temp Item")
        self.btn_add_temp.setStyleSheet("background-color: #f57f17; color: white; font-weight: bold;")
        self.btn_add_temp.clicked.connect(self.open_add_temp_item)
        layout.addWidget(self.btn_add_temp)
        
        self.btn_custom_pages = QPushButton("📎 Attach Pages")
        self.btn_custom_pages.setStyleSheet("background-color: #0277bd; color: white; font-weight: bold;")
        self.btn_custom_pages.clicked.connect(self.open_custom_pages)
        layout.addWidget(self.btn_custom_pages)
        
        self.btn_process_unmatched = QPushButton("⚙️ Process Unrecognized Items")
        self.btn_process_unmatched.setEnabled(False) # Disabled by default
        self.btn_process_unmatched.setStyleSheet("background-color: #424242; color: #888;")
        self.btn_process_unmatched.clicked.connect(self.open_batch_pdf)
        layout.addWidget(self.btn_process_unmatched)

        
        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        self.btn_gen_pdf = QPushButton("📄 Generate Client PDF")
        self.btn_gen_pdf.setStyleSheet("background-color: #2e7d32; color: white;")
        self.btn_gen_pdf.clicked.connect(self.generate_pdf)
        layout.addWidget(self.btn_gen_pdf)
        
        self.btn_gen_excel = QPushButton("📊 Generate Material Cart")
        self.btn_gen_excel.setStyleSheet("background-color: #6a1b9a; color: white;")
        self.btn_gen_excel.clicked.connect(self.generate_excel)
        layout.addWidget(self.btn_gen_excel)
        
        self.main_layout.addWidget(footer_frame)

    def _setup_status_bar(self):
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(5, 2, 5, 2)

        self.status_bar = QLabel("Ready.")
        self.status_bar.setStyleSheet("color: gray;")
        status_layout.addWidget(self.status_bar)

        status_layout.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0) # Indeterminate
        self.progress_bar.setMaximumHeight(12)
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setTextVisible(False)
        status_layout.addWidget(self.progress_bar)

        self.main_layout.addWidget(status_frame)

    def update_status(self, msg: str):
        self.status_bar.setText(msg)
        if self.ingestion_dialog and self.ingestion_dialog.isVisible():
            self.ingestion_dialog.append_log(msg)
        
    def _on_ollama_status(self, success: bool, err: str):
        if not success:
            role = ConfigManager.get("role") or "user"
            if role == "admin":
                self.status_bar.setText("⚠️ Ollama Offline (Start Ollama to use AI extraction)")
                self.status_bar.setStyleSheet("color: orange;")
            
    def show_error(self, err_msg: str):
        if self.ingestion_dialog:
            self.ingestion_dialog.append_log(f"❌ ERROR: {err_msg}")
            self.ingestion_dialog.set_finished()
        self._reset_ui_after_ingestion()
        QMessageBox.critical(self, "Error", err_msg)
        self.update_status("❌ Error occurred.")

    def toggle_debug(self, state):
        # state 2 is Checked, 0 is Unchecked
        self.controller.set_debug_mode(state == 2)

    def _reset_ui_after_ingestion(self):
        self.btn_load_dir.setEnabled(True)
        self.btn_load_dir.setText("📁 Pick Agreement")

    def load_directory(self):
        last_dir = ConfigManager.get("last_pdf_dir") or ""
        pdf_path, _ = QFileDialog.getOpenFileName(self, "Select Contract PDF", last_dir, "PDF Files (*.pdf)")
        if not pdf_path:
            return
            
        ConfigManager.set("last_pdf_dir", os.path.dirname(pdf_path))
            
        session_path = os.path.splitext(pdf_path)[0] + ".json"
        if os.path.exists(session_path):
            reply = QMessageBox.question(self, "Session Found", "A previous session exists for this PDF. Resume?", 
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.controller.load_session(session_path)
                return
                
        # Lock UI
        self.btn_load_dir.setEnabled(False)
        self.btn_load_dir.setText("⌛ Processing...")
        
        # Show verbose popup
        self.ingestion_dialog = IngestionProgressDialog(self)
        self.ingestion_dialog.show()
        
        self.update_status("📖 Reading PDF...")
        self.controller.start_ingestion(pdf_path)

    def save_session(self):
        success = self.controller.save_session(self.entry_client.text(), self.entry_po.text())
        if success:
            QMessageBox.information(self, "Saved", "Session saved successfully.")

    def generate_pdf(self):
        success, msg = self.controller.generate_pdf(self.entry_client.text(), self.entry_po.text())
        if success:
            self._set_generation_ui_busy(True)
        else:
            QMessageBox.warning(self, "Warning", msg)

    def generate_excel(self):
        success, msg = self.controller.generate_excel(self.entry_client.text(), self.entry_po.text())
        if success:
            self._set_generation_ui_busy(True)
        else:
            QMessageBox.warning(self, "Warning", msg)

    def _set_generation_ui_busy(self, busy: bool):
        self.btn_gen_pdf.setEnabled(not busy)
        self.btn_gen_excel.setEnabled(not busy)
        self.progress_bar.setVisible(busy)
        if busy:
            self.status_bar.setStyleSheet("color: #1976d2; font-weight: bold;")
        else:
            self.status_bar.setStyleSheet("color: gray;")

    def _on_generation_finished(self, task_type, file_path):
        self._set_generation_ui_busy(False)
        name = "PDF" if task_type == 'pdf' else "Excel"
        QMessageBox.information(self, "Success", f"{name} Generated!\nSaved to: {os.path.basename(file_path)}")
        self.update_status(f"✅ {name} saved successfully.")

    def _on_generation_error(self, task_type, err_msg):
        self._set_generation_ui_busy(False)
        name = "PDF" if task_type == 'pdf' else "Excel"
        QMessageBox.critical(self, "Error", f"Failed to generate {name}:\n{err_msg}")
        self.update_status(f"❌ {name} generation failed.")

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())

    def show_item_detail(self, idx):
        if getattr(self, '_detail_dialog_open', False):
            return
            
        items = self.controller.session_data.get("line_items", [])
        if 0 <= idx < len(items):
            self._detail_dialog_open = True
            try:
                ProductDetailDialog(self, idx, self.controller).exec()
            finally:
                self._detail_dialog_open = False

    def populate_ui(self, session_data=None):
        if self.ingestion_dialog:
            self.ingestion_dialog.set_finished()
        self._reset_ui_after_ingestion()
        
        if session_data is None:
            session_data = self.controller.session_data
            
        self.entry_client.setText(session_data.get("client_name", ""))
        self.entry_po.setText(session_data.get("project_po", ""))
        
        self.clear_layout(self.workspace_grid)
        
        items = session_data.get("line_items", [])
        hide_ignored = self.hide_ignored_var.isChecked()
        
        grid_row = 0
        for i, item in enumerate(items):
            meta = item.get("_match", {})
            match_id = meta.get("match_id")
            conf = meta.get("confidence", 0)
            color_hex = meta.get("color_hex", "#000000")
            is_ignored = meta.get("is_ignored", False)
            confirmed = item.get("confirmed", False)
            
            if is_ignored and hide_ignored:
                continue
                
            # --- Column 0: Contract Line ---
            left_row = ClickableRow(i, self.show_item_detail)
            left_l = QHBoxLayout(left_row)
            left_l.setContentsMargins(5, 5, 5, 5)
            
            # prefix_txt = f"{i+1}. [{item.get('room', 'Misc')}] Qty: {item.get('qty', 1)}"
            # lbl_prefix = QLabel(f"<b>{prefix_txt}</b>")
            # left_l.addWidget(lbl_prefix)
            
            lbl_num = QLabel(f"<b>{i+1}. [{item.get('room', 'Misc')}]</b>")
            left_l.addWidget(lbl_num)
            
            qty_layout = QHBoxLayout()
            qty_layout.setSpacing(2)
            
            btn_minus = QPushButton("-")
            btn_minus.setFixedSize(22, 22)
            btn_minus.setStyleSheet("background-color: #1976d2; color: white; border-radius: 11px; font-weight: bold; font-size: 14px;")
            btn_minus.clicked.connect(lambda checked, idx=i: self.update_item_qty(idx, -1))
            
            qty_val = item.get('qty', 1)
            lbl_qty = QLabel(f"Qty: <b>{qty_val}</b>")
            
            btn_plus = QPushButton("+")
            btn_plus.setFixedSize(22, 22)
            btn_plus.setStyleSheet("background-color: #1976d2; color: white; border-radius: 11px; font-weight: bold; font-size: 14px;")
            btn_plus.clicked.connect(lambda checked, idx=i: self.update_item_qty(idx, 1))
            
            qty_layout.addWidget(btn_minus)
            qty_layout.addWidget(lbl_qty)
            qty_layout.addWidget(btn_plus)
            left_l.addLayout(qty_layout)
            
            lbl_desc = QLabel(f"| {item.get('raw_description', '')}")
            lbl_desc.setWordWrap(True)
            left_l.addWidget(lbl_desc, 1)
            
            self.workspace_grid.addWidget(left_row, grid_row, 0)
            
            # --- Column 1: Match Details ---
            right_row = ClickableRow(i, self.show_item_detail)
            right_l = QHBoxLayout(right_row)
            right_l.setContentsMargins(5, 5, 5, 5)
            
            indicator = QLabel("●")
            indicator.setStyleSheet(f"color: {color_hex}; font-size: 20px;")
            right_l.addWidget(indicator)
            
            if confirmed:
                info_str = f"IGNORED: {match_id}" if is_ignored else f"CONFIRMED: {match_id}"
                btn_color = "#757575" if is_ignored else "#2e7d32"
                btn_text = "Unconfirm"
            else:
                info_str = f"Match: {match_id} ({conf:.1f}%)" if match_id else "No Match Found"
                btn_color = "#1565c0"
                btn_text = "Confirm"
                
            info_lbl = QLabel(info_str)
            right_l.addWidget(info_lbl, 1)
            
            # New "Change" / "Edit Temp" Button
            is_temp = item.get("is_temp", False)
            btn_change = QPushButton("Edit Temp" if is_temp else "Change")
            btn_change.setFixedWidth(80)
            btn_change.setStyleSheet("background-color: #424242; color: white;")
            if is_temp:
                btn_change.clicked.connect(lambda checked, i_idx=i: self.edit_temp_item(i_idx))
            else:
                btn_change.clicked.connect(lambda checked, i_idx=i: self.change_item_match(i_idx))
            right_l.addWidget(btn_change)
            
            btn_verify = QPushButton(btn_text)
            btn_verify.setFixedWidth(100)
            btn_verify.setStyleSheet(f"background-color: {btn_color}; color: white; font-weight: bold;")
            btn_verify.clicked.connect(lambda checked, idx=i, mid=match_id: self.toggle_confirm(idx, mid))
            right_l.addWidget(btn_verify)
            
            self.workspace_grid.addWidget(right_row, grid_row, 1)
            
            grid_row += 1

        # Update Process Unmatched button state
        unmatched = self.controller.get_unmatched_items()
        count = len(unmatched)
        role = ConfigManager.get("role") or "user"
        
        if count > 0 and role == "admin":
            self.btn_process_unmatched.setEnabled(True)
            self.btn_process_unmatched.setText(f"⚙️ Process Unrecognized Items ({count})")
            self.btn_process_unmatched.setStyleSheet("background-color: #0277bd; color: white; font-weight: bold;")
        else:
            self.btn_process_unmatched.setEnabled(False)
            text = f"⚙️ Process Unrecognized Items ({count})" if count > 0 else "⚙️ Process Unrecognized Items"
            if role != "admin":
                text += " (Admin Only)"
            self.btn_process_unmatched.setText(text)
            self.btn_process_unmatched.setStyleSheet("background-color: #424242; color: #888;")


    def toggle_confirm(self, idx, match_id):
        success, result = self.controller.toggle_item_confirmation(idx, match_id)
        if not success:
            QMessageBox.warning(self, "Warning", result)
        else:
            self.populate_ui()

    def change_item_match(self, idx):
        picker = DatabaseManager(self.controller, self, picker_mode=True)
        if picker.exec() == QDialog.DialogCode.Accepted and picker.selected_item_id:
            items = self.controller.session_data.get("line_items", [])
            if 0 <= idx < len(items):
                item = items[idx]
                if "_match" not in item:
                    item["_match"] = {}
                # Ensure we also get the newly selected item from the catalog to re-resolve confidence, color, ignored state.
                item["_match"]["match_id"] = picker.selected_item_id
                
                # Resolving match completely updates meta based on new match
                updated_meta = self.controller.resolve_match(item)
                item["_match"] = updated_meta
                item["confirmed"] = False
                
                self.populate_ui()
                return True
        return False

    def open_add_temp_item(self):
        dialog = TempItemEditDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted and hasattr(dialog, 'result_data'):
            if "line_items" not in self.controller.session_data:
                self.controller.session_data["line_items"] = []
            self.controller.session_data["line_items"].append(dialog.result_data)
            self.populate_ui()

    def open_custom_pages(self):
        dialog = CustomPagesDialog(self, self.controller.session_data)
        dialog.exec()
        self.populate_ui()

    def edit_temp_item(self, idx):
        items = self.controller.session_data.get("line_items", [])
        if 0 <= idx < len(items):
            item = items[idx]
            dialog = TempItemEditDialog(self, item_data=item)
            if dialog.exec() == QDialog.DialogCode.Accepted and hasattr(dialog, 'result_data'):
                items[idx] = dialog.result_data
                self.populate_ui()

    def update_item_qty(self, idx, delta):
        items = self.controller.session_data.get("line_items", [])
        if 0 <= idx < len(items):
            item = items[idx]
            current_qty = item.get("qty", 1)
            # Ensure quantity doesn't go below 1 (or 0 if allowed, let's say 1)
            new_qty = max(1, current_qty + delta)
            item["qty"] = new_qty
            self.populate_ui()
            return True
        return False

    def open_settings(self):
        SettingsWindow(self).exec()

    def open_database_manager(self):
        DatabaseManager(self.controller, self).exec()
        self.controller.refresh_catalog()
        if self.controller.session_data and "line_items" in self.controller.session_data:
            self.ingestion_dialog = IngestionProgressDialog(self)
            self.ingestion_dialog.setWindowTitle("Re-evaluating Matches")
            self.ingestion_dialog.show()
        self.controller.reevaluate_unmatched()

    def open_batch_pdf(self):
        unmatched = self.controller.get_unmatched_items()
        BatchPdfIngestWindow(self.controller, self, unmatched).exec()
        self.controller.refresh_catalog()
        if self.controller.session_data and "line_items" in self.controller.session_data:
            self.ingestion_dialog = IngestionProgressDialog(self)
            self.ingestion_dialog.setWindowTitle("Re-evaluating Matches")
            self.ingestion_dialog.show()
        self.controller.reevaluate_unmatched()

    def open_sync_dialog(self, is_publish=False):
        owner = ConfigManager.get("github_owner") or "YOUR_COMPANY_GITHUB_USERNAME"
        repo = ConfigManager.get("github_repo") or "material-confirmation-db"
        token = ConfigManager.get("github_token")
        local_path = self.controller.db_loader.base_path
        
        if is_publish and not token:
            QMessageBox.warning(self, "Missing Token", "You cannot publish without an Admin Token. Please set it in settings.json.")
            return

        dialog = SyncProgressDialog(self, is_publish=is_publish)
        dialog.show()
        dialog.start_sync(owner, repo, token, local_path)
        
        # When closed, refresh DB if it was a download sync
        dialog.exec()
        if not is_publish:
            self.controller.refresh_catalog()
            if self.controller.session_data and "line_items" in self.controller.session_data:
                self.ingestion_dialog = IngestionProgressDialog(self)
                self.ingestion_dialog.setWindowTitle("Re-evaluating Matches")
                self.ingestion_dialog.show()
            self.controller.reevaluate_unmatched()

    def closeEvent(self, event):
        is_maximized = self.isMaximized()
        ConfigManager.set("main_window_maximized", is_maximized)
        
        if not is_maximized:
            ConfigManager.set("main_window_width", self.width())
            ConfigManager.set("main_window_height", self.height())
            ConfigManager.set("main_window_x", self.x())
            ConfigManager.set("main_window_y", self.y())
            
        event.accept()
