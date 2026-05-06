import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QPushButton, QLineEdit, QCheckBox, 
                               QScrollArea, QFrame, QFileDialog, QMessageBox, QSizePolicy, QSpacerItem)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon

from models.config_manager import ConfigManager
from ui.settings import SettingsWindow
from ui.database_manager import DatabaseManager
from ui.batch_pdf import BatchPdfIngestWindow
from ui.ingestion_progress import IngestionProgressDialog
from ui.product_detail import ProductDetailDialog

class ClickableRow(QFrame):
    def __init__(self, index, callback):
        super().__init__()
        self.index = index
        self.callback = callback
        self.setCursor(Qt.PointingHandCursor)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.callback(self.index)
        super().mousePressEvent(event)

class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.ingestion_dialog = None
        
        self.setWindowTitle("PKB ERP Command Center v3.0 (Qt)")
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
            self.setWindowState(Qt.WindowMaximized)
        
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
        
        # Start Ollama check
        self.controller.check_ollama_background()

    def _setup_header(self):
        header_frame = QFrame()
        layout = QHBoxLayout(header_frame)
        
        title_lbl = QLabel("Command Center")
        title_lbl.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title_lbl)
        
        self.btn_load_dir = QPushButton("📁 Pick Agreement")
        self.btn_load_dir.clicked.connect(self.load_directory)
        layout.addWidget(self.btn_load_dir)
        
        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        self.debug_var = QCheckBox("Enable Developer Logging")
        self.debug_var.stateChanged.connect(self.toggle_debug)
        layout.addWidget(self.debug_var)
        
        self.btn_manage_db = QPushButton("⚙️ Manage Database")
        self.btn_manage_db.setStyleSheet("background-color: #1565c0; color: white;")
        self.btn_manage_db.clicked.connect(self.open_database_manager)
        layout.addWidget(self.btn_manage_db)
        
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
        
        i_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
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
        self.workspace_grid.setAlignment(Qt.AlignTop)
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
        
        self.btn_process_unmatched = QPushButton("⚙️ Process Unrecognized Items")
        self.btn_process_unmatched.setEnabled(False) # Disabled by default
        self.btn_process_unmatched.setStyleSheet("background-color: #424242; color: #888;")
        self.btn_process_unmatched.clicked.connect(self.open_batch_pdf)
        layout.addWidget(self.btn_process_unmatched)

        
        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
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
        self.status_bar = QLabel("Ready.")
        self.status_bar.setStyleSheet("color: gray;")
        self.main_layout.addWidget(self.status_bar)

    def update_status(self, msg: str):
        self.status_bar.setText(msg)
        if self.ingestion_dialog and self.ingestion_dialog.isVisible():
            self.ingestion_dialog.append_log(msg)
        
    def _on_ollama_status(self, success: bool, err: str):
        if not success:
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
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
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
            QMessageBox.information(self, "Success", f"Client PDF Generated!\n{msg}")
        else:
            QMessageBox.warning(self, "Warning", msg)

    def generate_excel(self):
        success, msg = self.controller.generate_excel(self.entry_client.text(), self.entry_po.text())
        if success:
            QMessageBox.information(self, "Success", f"Material Cart Excel Generated!\n{msg}")
        else:
            QMessageBox.warning(self, "Warning", msg)

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
        items = self.controller.session_data.get("line_items", [])
        if 0 <= idx < len(items):
            ProductDetailDialog(self, idx, self.controller).exec()

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
            
            prefix_txt = f"{i+1}. [{item.get('room', 'Misc')}] Qty: {item.get('qty', 1)}"
            lbl_prefix = QLabel(f"<b>{prefix_txt}</b>")
            left_l.addWidget(lbl_prefix)
            
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
            
            # New "Change" Button
            btn_change = QPushButton("Change")
            btn_change.setFixedWidth(80)
            btn_change.setStyleSheet("background-color: #424242; color: white;")
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
        if count > 0:
            self.btn_process_unmatched.setEnabled(True)
            self.btn_process_unmatched.setText(f"⚙️ Process Unrecognized Items ({count})")
            self.btn_process_unmatched.setStyleSheet("background-color: #0277bd; color: white; font-weight: bold;")
        else:
            self.btn_process_unmatched.setEnabled(False)
            self.btn_process_unmatched.setText("⚙️ Process Unrecognized Items")
            self.btn_process_unmatched.setStyleSheet("background-color: #424242; color: #888;")


    def toggle_confirm(self, idx, match_id):
        success, result = self.controller.toggle_item_confirmation(idx, match_id)
        if not success:
            QMessageBox.warning(self, "Warning", result)
        else:
            self.populate_ui()

    def change_item_match(self, idx):
        picker = DatabaseManager(self.controller, self, picker_mode=True)
        if picker.exec() == QDialog.Accepted and picker.selected_item_id:
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

    def open_settings(self):
        SettingsWindow(self).exec()

    def open_database_manager(self):
        DatabaseManager(self.controller, self).exec()

    def open_batch_pdf(self):
        unmatched = self.controller.get_unmatched_items()
        BatchPdfIngestWindow(self.controller, self, unmatched).exec()

    def closeEvent(self, event):
        is_maximized = self.isMaximized()
        ConfigManager.set("main_window_maximized", is_maximized)
        
        if not is_maximized:
            ConfigManager.set("main_window_width", self.width())
            ConfigManager.set("main_window_height", self.height())
            ConfigManager.set("main_window_x", self.x())
            ConfigManager.set("main_window_y", self.y())
            
        event.accept()
