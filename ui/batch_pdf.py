import os
from PySide6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QLineEdit, QComboBox, 
                               QTableView, QFrame, QFileDialog, QMessageBox, QProgressBar, QTextEdit)
from PySide6.QtCore import Qt, QAbstractTableModel
from core.app_controller import AppController

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
        
        form_layout = QHBoxLayout()
        form_left = QVBoxLayout()
        form_right = QVBoxLayout()
        
        form_left.addWidget(QLabel("Category File *"))
        self.cat_entry = QComboBox()
        self.cat_entry.addItems(self._get_existing_categories())
        form_left.addWidget(self.cat_entry)
        
        form_left.addWidget(QLabel("Unique ID *"))
        self.id_entry = QLineEdit()
        form_left.addWidget(self.id_entry)
        
        form_left.addWidget(QLabel("Brand"))
        self.brand_entry = QLineEdit()
        form_left.addWidget(self.brand_entry)
        
        form_left.addWidget(QLabel("OneClick Description *"))
        self.oneclick_entry = QLineEdit()
        form_left.addWidget(self.oneclick_entry)
        
        form_left.addWidget(QLabel("Routing Tag *"))
        self.routing_entry = QComboBox()
        self.routing_entry.addItems(["IGNORE", "WAREHOUSE", "PROCURE", "WH_OR_PROCURE"])
        form_left.addWidget(self.routing_entry)
        
        form_right.addWidget(QLabel("Finish (Color)"))
        self.finish_entry = QLineEdit()
        form_right.addWidget(self.finish_entry)
        
        form_right.addWidget(QLabel("Marketing Description"))
        self.desc_entry = QLineEdit()
        form_right.addWidget(self.desc_entry)
        
        form_layout.addLayout(form_left)
        form_layout.addLayout(form_right)
        right_layout.addLayout(form_layout)
        
        self.btn_save = QPushButton("Save")
        self.btn_save.setStyleSheet("background-color: #2e7d32; color: white;")
        self.btn_save.clicked.connect(self.initiate_save)
        right_layout.addWidget(self.btn_save)
        
        self.progress_bar = QProgressBar()

        self.progress_bar.setRange(0, 0) # Indeterminate
        self.progress_bar.hide()
        right_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(right_frame, 2)
        
    def log_to_console(self, msg):
        pass # Console removed
        
    def _get_existing_categories(self):
        categories_path = "database/categories"
        if not os.path.exists(categories_path): return []
        return [f for f in os.listdir(categories_path) if f.endswith('.yaml')]

    def on_table_click(self, index):
        item = self.table_model.get_item(index.row())
        if item:
            self.oneclick_entry.setText(item.get("raw_description", ""))
            self.log_to_console(f"Selected item: {item.get('raw_description')}")
            
    def initiate_save(self):
        QMessageBox.information(self, "Save", "Save logic to be wired to ProductService.")
