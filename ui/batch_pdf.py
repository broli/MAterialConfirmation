import os
from PySide6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QLineEdit, QComboBox, 
                               QTableView, QFrame, QFileDialog, QMessageBox, QProgressBar, QTextEdit)
from PySide6.QtCore import Qt, QAbstractTableModel
from core.app_controller import AppController
from ui.components.product_form import ProductFormWidget

class QueueTableModel(QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self._data = data or []
        self._headers = ["Description", "Status"]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            item = self._data[index.row()]
            if index.column() == 0:
                return item.get("raw_description", "")
            elif index.column() == 1:
                return "Pending"
        return None

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        return None

    def update_data(self, new_data):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

    def get_item(self, row):
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

class BatchPdfIngestWindow(QDialog):
    def __init__(self, controller: AppController, parent=None, unmatched_items=None):
        super().__init__(parent)
        self.controller = controller
        
        self.setWindowTitle("Batch Add Unmatched PDF Items")
        self.resize(1200, 800)
        self.db_modified = False
        
        self.unmatched_items = unmatched_items or []
        
        main_layout = QHBoxLayout(self)
        
        # Left Pane
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        left_layout.addWidget(QLabel("<b>1. Unmatched Items Queue</b>"))

        
        self.table_view = QTableView()
        self.table_model = QueueTableModel(self.unmatched_items)
        self.table_view.setModel(self.table_model)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setColumnWidth(0, 400)
        self.table_view.clicked.connect(self.on_table_click)
        left_layout.addWidget(self.table_view)
        
        main_layout.addWidget(left_frame, 1)
        
        # Right Pane
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.addWidget(QLabel("<b>2. Modify extracted details</b>"))
        
        self.form = ProductFormWidget(self, categories_path=os.path.join(self.controller.db_loader.base_path, "categories"))
        self.form.copy_from_requested.connect(self._on_copy_from_requested)
        right_layout.addWidget(self.form)
        
        self.btn_save = QPushButton("Save to Database")
        self.btn_save.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold;")
        self.btn_save.clicked.connect(self.initiate_save)
        right_layout.addWidget(self.btn_save)
        
        self.progress_bar = QProgressBar()

        self.progress_bar.setRange(0, 0) # Indeterminate
        self.progress_bar.hide()
        right_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(right_frame, 2)

    def _on_copy_from_requested(self):
        from ui.database_manager import DatabaseManager
        dlg = DatabaseManager(self.controller, parent=self, picker_mode=True)
        if dlg.exec():
            item_id = dlg.selected_item_id
            if item_id:
                item_full = self.controller.catalog.get(item_id)
                if not item_full: return
                
                msg = QMessageBox(self)
                msg.setWindowTitle("Merge Strategy")
                msg.setText("How would you like to merge this data?")
                btn_overwrite = msg.addButton("Overwrite Existing Data", QMessageBox.ButtonRole.AcceptRole)
                btn_fill = msg.addButton("Fill Empty Fields Only", QMessageBox.ButtonRole.AcceptRole)
                msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
                
                msg.exec()
                
                if msg.clickedButton() == btn_overwrite:
                    self.form.copy_from(item_full, item_full.get("category_file", ""), "overwrite")
                elif msg.clickedButton() == btn_fill:
                    self.form.copy_from(item_full, item_full.get("category_file", ""), "fill_empty")
        
    def log_to_console(self, msg):
        pass # Console removed
        
    def on_table_click(self, index):
        item = self.table_model.get_item(index.row())
        if item:
            extracted = item.get("_match", {}).get("extracted_fields") or {}
            
            # Map LLM extractions to the expected database schema
            mapped_data = {
                "id": "", # ID should be assigned manually by user
                "sku": item.get("sku", ""),
                "brand": extracted.get("brand", ""),
                "oneclick_description": item.get("raw_description", ""),
                "routing_tag": "WAREHOUSE",
            }
            
            # Map LLM-extracted printable properties
            printable = {}
            if extracted.get("finish"): printable["finish"] = extracted["finish"]
            if extracted.get("base_item"): printable["description"] = extracted["base_item"]
            if extracted.get("dimensions"): printable["dimensions"] = extracted["dimensions"]
            
            if printable:
                mapped_data["printable"] = printable
                
            category = extracted.get("category", "")
            self.form.load_data(mapped_data, category)
            
    def initiate_save(self):
        data, category = self.form.get_data()
        
        if not data.get("id"):
            QMessageBox.warning(self, "Validation Error", "ID is required.")
            return
            
        if not category:
            QMessageBox.warning(self, "Validation Error", "Category is required.")
            return
            
        try:
            from models.product_service import ProductService
            categories_path = os.path.join(self.controller.db_loader.base_path, "categories")
            assets_path = os.path.join(self.controller.db_loader.base_path, "assets")
            ProductService.upsert_to_yaml(data, str(category), categories_path, assets_path)
            self.db_modified = True
            QMessageBox.information(self, "Success", "Item saved successfully!")
            
            # Remove from unmatched queue visually
            rows = self.table_view.selectionModel().selectedRows()
            if rows:
                row = rows[0].row()
                self.unmatched_items.pop(row)
                self.table_model.update_data(self.unmatched_items)
                self.form.load_data({}) # Clear form
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")

