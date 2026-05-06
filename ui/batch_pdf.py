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

    def data(self, index, role):
        if role == Qt.DisplayRole:
            item = self._data[index.row()]
            if index.column() == 0:
                desc = item.get("raw_description", "")
                return desc if len(desc) < 40 else desc[:37] + "..."
            elif index.column() == 1:
                return "Pending"
        return None

    def rowCount(self, index=None):
        return len(self._data)

    def columnCount(self, index=None):
        return len(self._headers)

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
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
        
        self.unmatched_items = unmatched_items or []
        
        main_layout = QHBoxLayout(self)
        
        # Left Pane
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        left_layout.addWidget(QLabel("<b>1. Unmatched Items Queue</b>"))

        
        self.table_view = QTableView()
        self.table_model = QueueTableModel(self.unmatched_items)
        self.table_view.setModel(self.table_model)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.clicked.connect(self.on_table_click)
        left_layout.addWidget(self.table_view)
        
        main_layout.addWidget(left_frame, 1)
        
        # Right Pane
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.addWidget(QLabel("<b>2. Modify extracted details</b>"))
        
        self.form = ProductFormWidget(self, categories_path=os.path.join(self.controller.db_loader.base_path, "categories"))
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
        
    def log_to_console(self, msg):
        pass # Console removed
        
    def on_table_click(self, index):
        item = self.table_model.get_item(index.row())
        if item:
            # Map LLM extractions to the expected database schema
            mapped_data = {
                "id": "", # ID should be assigned manually by user
                "sku": item.get("sku", ""),
                "brand": item.get("brand", ""),
                "oneclick_description": item.get("raw_description", ""),
                "routing_tag": "WAREHOUSE",
            }
            
            # Map LLM-extracted printable properties
            printable = {}
            if item.get("finish"): printable["finish"] = item["finish"]
            if item.get("base_item"): printable["description"] = item["base_item"]
            if item.get("dimensions"): printable["dimensions"] = item["dimensions"]
            
            if printable:
                mapped_data["printable"] = printable
                
            self.form.load_data(mapped_data)
            
    def initiate_save(self):
        data, category = self.form.get_data()
        
        if not data.get("id"):
            QMessageBox.warning(self, "Validation Error", "ID is required.")
            return
            
        try:
            from models.product_service import ProductService
            categories_path = os.path.join(self.controller.db_loader.base_path, "categories")
            assets_path = os.path.join(self.controller.db_loader.base_path, "assets")
            ProductService.upsert_to_yaml(data, category, categories_path, assets_path)
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

