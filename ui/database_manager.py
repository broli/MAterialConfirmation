import os
from PySide6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QLineEdit, QComboBox, 
                               QTableView, QFrame, QFileDialog, QMessageBox, 
                               QScrollArea, QCheckBox, QTextEdit, QHeaderView)
from PySide6.QtCore import Qt, QAbstractTableModel
from models.config_manager import ConfigManager
from models.product_service import ProductService
from ui.components.product_form import ProductFormWidget

class CatalogTableModel(QAbstractTableModel):
    def __init__(self, catalog=None):
        super().__init__()
        self._catalog = catalog or {}
        self._filter_text = ""
        self._data = []
        self._headers = ["Category", "ID", "SKU", "Brand", "Routing", "Description"]
        self._update_internal_data()


    def _update_internal_data(self):
        self._data = []
        filter_lower = self._filter_text.lower()
        
        for item_id, item in self._catalog.items():
            cat = item.get("category_file", "").replace(".yaml", "")
            sku = item.get("sku", "")
            brand = item.get("brand", "")
            routing = item.get("routing_tag", "")
            desc = item.get("oneclick_description", "")
            
            # Search across all fields
            search_blob = f"{cat} {item_id} {sku} {brand} {routing} {desc}".lower()
            
            if not self._filter_text or filter_lower in search_blob:
                self._data.append({
                    "category": cat,
                    "id": item_id,
                    "sku": sku,
                    "brand": brand,
                    "routing": routing,
                    "description": desc
                })
        # Sort by category then ID
        self._data.sort(key=lambda x: (x["category"], x["id"]))

    def set_filter(self, text):
        self.beginResetModel()
        self._filter_text = text
        self._update_internal_data()
        self.endResetModel()


    def update_catalog(self, new_catalog):
        self.beginResetModel()
        self._catalog = new_catalog
        self._update_internal_data()
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role):
        if not index.isValid(): return None
        if role == Qt.DisplayRole:
            row = self._data[index.row()]
            col = index.column()
            if col == 0: return row["category"]
            elif col == 1: return row["id"]
            elif col == 2: return row["sku"]
            elif col == 3: return row["brand"]
            elif col == 4: return row["routing"]
            elif col == 5: 
                desc = row["description"]
                return desc if len(desc) < 60 else desc[:57] + "..."
        return None

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None
        
    def get_item_id(self, row_idx):
        if 0 <= row_idx < len(self._data):
            return self._data[row_idx]["id"]
        return None

class ProductEditDialog(QDialog):
    def __init__(self, parent, product_service, categories_path, assets_path, product=None):
        super().__init__(parent)
        self.product_service = product_service
        self.categories_path = categories_path
        self.assets_path = assets_path
        self.product = product or {}
        self.is_new = product is None
        
        self.setWindowTitle("Add/Edit Product" if self.is_new else f"Edit Product: {self.product.get('id')}")
        self.resize(600, 700)
        
        layout = QVBoxLayout(self)
        
        # Form Widget
        self.form = ProductFormWidget(self, categories_path=self.categories_path)
        self.form.load_data(self.product, self.product.get("category_file", ""))
        layout.addWidget(self.form)
        
        # Footer
        footer = QHBoxLayout()
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.save)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        footer.addStretch()
        footer.addWidget(btn_save)
        footer.addWidget(btn_cancel)
        layout.addLayout(footer)

    def save(self):
        data, category = self.form.get_data()
        
        if not data.get("id"):
            QMessageBox.warning(self, "Validation Error", "ID is required.")
            return
            
        try:
            self.product_service.upsert_to_yaml(data, category, self.categories_path, self.assets_path)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")


class DatabaseManager(QDialog):
    def __init__(self, controller, parent=None, picker_mode=False):
        super().__init__(parent)
        self.controller = controller
        self.db_loader = controller.db_loader
        self.product_service = ProductService()
        self.categories_path = os.path.join(self.db_loader.base_path, "categories")
        self.assets_path = os.path.join(self.db_loader.base_path, "assets")
        self.picker_mode = picker_mode
        self.selected_item_id = None
        
        self.setWindowTitle("Catalog Manager (Qt)" if not picker_mode else "Select Item")
        self.resize(1000, 700)
        
        # We will use a stacked layout approach by just hiding/showing frames
        self.main_layout = QVBoxLayout(self)
        
        self._build_browser_view()
        
        # Load data
        self.table_model = CatalogTableModel(self.controller.catalog)
        self.table_view.setModel(self.table_model)
        self.table_view.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        
    def _build_browser_view(self):
        self.browser_frame = QFrame()
        layout = QVBoxLayout(self.browser_frame)
        
        header = QHBoxLayout()
        header.addWidget(QLabel("<h2>Database Browser</h2>"))
        header.addStretch()
        
        btn_add = QPushButton("Add New Item")
        btn_add.setStyleSheet("background-color: #2e7d32; color: white;")
        btn_add.clicked.connect(self.show_add_form)
        header.addWidget(btn_add)
        
        layout.addLayout(header)
        
        # Search Bar
        search_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Search by ID, SKU, Brand, or Description...")
        self.search_bar.setClearButtonEnabled(True) # Standard looking clear button
        self.search_bar.setMinimumHeight(35)
        self.search_bar.setStyleSheet("font-size: 14px; padding-left: 10px;")
        self.search_bar.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_bar)
        layout.addLayout(search_layout)
        
        self.table_view = QTableView()

        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.doubleClicked.connect(self.on_row_double_click)
        layout.addWidget(self.table_view)
        
        if self.picker_mode:
            footer = QHBoxLayout()
            btn_select = QPushButton("Select Highlighted Item")
            btn_select.setStyleSheet("background-color: #1565c0; color: white;")
            btn_select.clicked.connect(self.on_select_clicked)
            footer.addStretch()
            footer.addWidget(btn_select)
            layout.addLayout(footer)
            
            # Hide the Add New Item button in picker mode if desired, but we can leave it.
            btn_add.setVisible(False)
            
        self.main_layout.addWidget(self.browser_frame)

    def on_row_double_click(self, index):
        item_id = self.table_model.get_item_id(index.row())
        if item_id:
            if self.picker_mode:
                self.selected_item_id = item_id
                self.accept()
            else:
                self.show_edit_form(item_id)

    def on_select_clicked(self):
        indexes = self.table_view.selectionModel().selectedRows()
        if indexes:
            item_id = self.table_model.get_item_id(indexes[0].row())
            if item_id:
                self.selected_item_id = item_id
                self.accept()
        else:
            QMessageBox.warning(self, "Warning", "Please select an item first.")

    def show_add_form(self):
        dlg = ProductEditDialog(self, self.product_service, self.categories_path, self.assets_path)
        if dlg.exec():
            self.refresh_data()

    def show_edit_form(self, item_id):
        # Find item in catalog
        product = self.controller.find_product_by_id(item_id)
        if product:
            dlg = ProductEditDialog(self, self.product_service, self.categories_path, self.assets_path, product)
            if dlg.exec():
                self.refresh_data()

    def refresh_data(self):
        self.controller.refresh_catalog()
        # Preserve filter if any
        self.table_model.update_catalog(self.controller.catalog)

    def on_search_changed(self, text):
        self.table_model.set_filter(text)
