import os
import shutil
from PySide6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QLineEdit, QComboBox, 
                               QTableView, QFrame, QFileDialog, QMessageBox, 
                               QScrollArea, QHeaderView, QProgressDialog, QAbstractItemView)
from PySide6.QtCore import Qt, QAbstractTableModel, QSortFilterProxyModel, QThread
from models.config_manager import ConfigManager
from models.product_service import ProductService
from models.catalog_loader import CatalogLoader
from ui.components.product_form import ProductFormWidget
from core.bulk_worker import BulkIngestWorker
from ui.ingestion_progress import IngestionProgressDialog

class CatalogTableModel(QAbstractTableModel):
    def __init__(self, catalog=None):
        super().__init__()
        self._catalog = catalog or {}
        self._data = []
        self._headers = ["Category", "ID", "SKU", "Brand", "Routing", "Description"]
        self._update_internal_data()

    def _update_internal_data(self):
        self._data = []
        for item_id, item in self._catalog.items():
            cat = item.get("category_file", "").replace(".yaml", "")
            sku = item.get("sku", "UNKNOWN")
            brand = item.get("brand", "UNKNOWN")
            routing = item.get("routing_tag", "UNKNOWN")
            desc = item.get("oneclick_description", "")
            
            self._data.append({
                "category": cat,
                "id": item_id,
                "sku": sku,
                "brand": brand,
                "routing": routing,
                "description": desc,
                "full_item": item
            })

    def update_catalog(self, new_catalog):
        self.beginResetModel()
        self._catalog = new_catalog
        self._update_internal_data()
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid(): return None
        if role == Qt.ItemDataRole.DisplayRole:
            row = self._data[index.row()]
            col = index.column()
            if col == 0: return row["category"]
            elif col == 1: return row["id"]
            elif col == 2: return row["sku"]
            elif col == 3: return row["brand"]
            elif col == 4: return row["routing"]
            elif col == 5: 
                desc = row["description"]
                return desc if len(desc) < 80 else desc[:77] + "..."
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        return None
        
    def get_item_id(self, row_idx):
        if 0 <= row_idx < len(self._data):
            return self._data[row_idx]["id"]
        return None
        
    def get_full_item(self, row_idx):
        if 0 <= row_idx < len(self._data):
            return self._data[row_idx]["full_item"]
        return None


class BatchEditDialog(QDialog):
    def __init__(self, parent, selected_count):
        super().__init__(parent)
        self.setWindowTitle(f"Batch Edit ({selected_count} items)")
        self.resize(400, 250)
        self.result_data = {}
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select a field to modify for all selected items:"))
        
        form_layout = QHBoxLayout()
        self.field_combo = QComboBox()
        self.field_combo.addItems(["brand", "category_file", "routing_tag"])
        form_layout.addWidget(self.field_combo)
        
        self.value_entry = QLineEdit()
        self.value_entry.setPlaceholderText("New value...")
        form_layout.addWidget(self.value_entry)
        
        layout.addLayout(form_layout)
        
        footer = QHBoxLayout()
        btn_apply = QPushButton("Apply to All")
        btn_apply.setStyleSheet("background-color: #f57c00; color: white; font-weight: bold;")
        btn_apply.clicked.connect(self.apply)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        footer.addStretch()
        footer.addWidget(btn_apply)
        footer.addWidget(btn_cancel)
        layout.addLayout(footer)
        
    def apply(self):
        field = self.field_combo.currentText()
        val = self.value_entry.text().strip()
        if not val:
            QMessageBox.warning(self, "Warning", "Value cannot be empty.")
            return
            
        if field == "category_file" and not val.endswith(".yaml"):
            val += ".yaml"
            
        self.result_data = {field: val}
        self.accept()


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
        
        self.form = ProductFormWidget(self, categories_path=self.categories_path)
        self.form.load_data(self.product, self.product.get("category_file", ""))
        layout.addWidget(self.form)
        
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
            from models.product_service import ProductService
            data["id"] = ProductService.get_next_id(category, self.categories_path)
            self.form.id_entry.setText(data["id"])
            
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
        self.picker_mode = picker_mode
        self.selected_item_id = None
        self.db_modified = False
        
        # State tracking
        self.current_source = "Production"
        
        self.setWindowTitle("Catalog Manager (Qt)" if not picker_mode else "Select Item")
        self.resize(1100, 750)
        
        self.main_layout = QVBoxLayout(self)
        self._build_browser_view()
        self._refresh_loaders()
        
    def _refresh_loaders(self):
        # Refresh both loaders
        self.db_loader.load_all_categories()
        
        staging_dir = "staging_database"
        os.makedirs(os.path.join(staging_dir, "categories"), exist_ok=True)
        os.makedirs(os.path.join(staging_dir, "assets"), exist_ok=True)
        self.staging_loader = CatalogLoader(base_path=staging_dir)
        self.staging_catalog = self.staging_loader.load_all_categories()
        
        self.refresh_data()

    def get_current_paths(self):
        base = "database" if self.current_source == "Production" else "staging_database"
        return os.path.join(base, "categories"), os.path.join(base, "assets")

    def _build_browser_view(self):
        # Top Controls
        top_controls = QHBoxLayout()
        
        self.source_combo = QComboBox()
        self.source_combo.addItems(["Production", "Staging Area"])
        self.source_combo.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        self.source_combo.currentTextChanged.connect(self.on_source_changed)
        top_controls.addWidget(self.source_combo)
        
        top_controls.addStretch()
        
        self.btn_bulk_ingest = QPushButton("📥 Start Bulk Ingestion")
        self.btn_bulk_ingest.setStyleSheet("background-color: #6a1b9a; color: white;")
        self.btn_bulk_ingest.clicked.connect(self.start_bulk_ingestion)
        # Only admin sees this
        if ConfigManager.get("role") != "admin":
            self.btn_bulk_ingest.hide()
            self.source_combo.hide() # Maybe hide staging from non-admins too
        top_controls.addWidget(self.btn_bulk_ingest)
        
        self.btn_add = QPushButton("➕ Add New Item")
        self.btn_add.setStyleSheet("background-color: #2e7d32; color: white;")
        self.btn_add.clicked.connect(self.show_add_form)
        top_controls.addWidget(self.btn_add)
        
        self.main_layout.addLayout(top_controls)
        
        # Search Bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Search by ID, SKU, Brand, or Description...")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.setMinimumHeight(35)
        self.search_bar.textChanged.connect(self.on_search_changed)
        self.main_layout.addWidget(self.search_bar)
        
        # Table
        self.table_model = CatalogTableModel()
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(-1) # Filter all columns
        
        self.table_view = QTableView()
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection) # Multi-select
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(True)
        self.table_view.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table_view.doubleClicked.connect(self.on_row_double_click)
        self.main_layout.addWidget(self.table_view)
        
        # Action Footer
        self.footer_layout = QHBoxLayout()
        
        self.btn_batch_edit = QPushButton("✏️ Batch Edit Selected")
        self.btn_batch_edit.setStyleSheet("background-color: #f57c00; color: white; font-weight: bold;")
        self.btn_batch_edit.clicked.connect(self.on_batch_edit)
        self.footer_layout.addWidget(self.btn_batch_edit)
        
        self.btn_approve = QPushButton("✅ Approve Selected to Production")
        self.btn_approve.setStyleSheet("background-color: #1565c0; color: white; font-weight: bold;")
        self.btn_approve.clicked.connect(self.on_approve_selected)
        self.btn_approve.hide() # Hidden by default, shown in Staging
        self.footer_layout.addWidget(self.btn_approve)
        
        self.footer_layout.addStretch()
        
        if self.picker_mode:
            btn_select = QPushButton("Select Item")
            btn_select.setStyleSheet("background-color: #1565c0; color: white;")
            btn_select.clicked.connect(self.on_select_clicked)
            self.footer_layout.addWidget(btn_select)
            self.btn_add.setVisible(False)
            self.btn_batch_edit.hide()
            
        self.main_layout.addLayout(self.footer_layout)

    def on_source_changed(self, text):
        self.current_source = text
        if text == "Staging Area":
            self.btn_approve.show()
            self.btn_add.hide()
        else:
            self.btn_approve.hide()
            self.btn_add.show()
        self.refresh_data()

    def refresh_data(self):
        cat = self.controller.catalog if self.current_source == "Production" else self.staging_catalog
        self.table_model.update_catalog(cat)
        self.db_modified = True

    def on_search_changed(self, text):
        # QSortFilterProxyModel handles searching automatically
        self.proxy_model.setFilterFixedString(text)

    def get_selected_items(self):
        indexes = self.table_view.selectionModel().selectedRows()
        items = []
        for idx in indexes:
            source_idx = self.proxy_model.mapToSource(idx)
            item_full = self.table_model.get_full_item(source_idx.row())
            if item_full: items.append(item_full)
        return items

    def on_batch_edit(self):
        items = self.get_selected_items()
        if not items:
            QMessageBox.warning(self, "Warning", "Select items to batch edit.")
            return
            
        dlg = BatchEditDialog(self, len(items))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            field = list(dlg.result_data.keys())[0]
            val = dlg.result_data[field]
            
            cat_path, ass_path = self.get_current_paths()
            
            # Apply to all
            for item in items:
                old_cat = item.get("category_file", "")
                
                # Apply change
                item[field] = val
                
                new_cat = item.get("category_file", "")
                
                # If category changed, we might need to delete old YAML if it was the only item
                # For simplicity, we just upsert. The ProductService manages file writing.
                self.product_service.upsert_to_yaml(item, new_cat, cat_path, ass_path)
            
            self._refresh_loaders()
            QMessageBox.information(self, "Success", f"Batch edit applied to {len(items)} items.")

    def on_approve_selected(self):
        items = self.get_selected_items()
        if not items:
            QMessageBox.warning(self, "Warning", "Select items to approve.")
            return
            
        prod_cat_path = os.path.join("database", "categories")
        prod_ass_path = os.path.join("database", "assets")
        
        stg_cat_path = os.path.join("staging_database", "categories")
        
        for item in items:
            # 1. Upsert to production
            cat_file = item.get("category_file", "UNKNOWN.yaml")
            self.product_service.upsert_to_yaml(item, cat_file, prod_cat_path, prod_ass_path)
            
            # 2. Remove from staging (by deleting it from the staging YAML)
            stg_file_path = os.path.join(stg_cat_path, cat_file)
            if os.path.exists(stg_file_path):
                import yaml
                with open(stg_file_path, "r", encoding="utf-8") as f:
                    docs = list(yaml.safe_load_all(f))
                
                new_docs = [d for d in docs if d and d.get("id") != item["id"]]
                
                if new_docs:
                    with open(stg_file_path, "w", encoding="utf-8") as f:
                        yaml.safe_dump_all(new_docs, f, sort_keys=False)
                else:
                    os.remove(stg_file_path) # Delete empty file
                    
        self._refresh_loaders()
        QMessageBox.information(self, "Success", f"Approved {len(items)} items to production.")

    def show_add_form(self):
        cat_path, ass_path = self.get_current_paths()
        dlg = ProductEditDialog(self, self.product_service, cat_path, ass_path)
        if dlg.exec():
            self._refresh_loaders()

    def show_edit_form(self, item_full):
        cat_path, ass_path = self.get_current_paths()
        dlg = ProductEditDialog(self, self.product_service, cat_path, ass_path, item_full)
        if dlg.exec():
            self._refresh_loaders()

    def on_row_double_click(self, index):
        source_idx = self.proxy_model.mapToSource(index)
        item_id = self.table_model.get_item_id(source_idx.row())
        item_full = self.table_model.get_full_item(source_idx.row())
        
        if item_id:
            if self.picker_mode:
                self.selected_item_id = item_id
                self.accept()
            else:
                self.show_edit_form(item_full)

    def on_select_clicked(self):
        indexes = self.table_view.selectionModel().selectedRows()
        if indexes:
            source_idx = self.proxy_model.mapToSource(indexes[0])
            item_id = self.table_model.get_item_id(source_idx.row())
            if item_id:
                self.selected_item_id = item_id
                self.accept()

    def start_bulk_ingestion(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder of PDF JSONs")
        if not folder_path:
            return
            
        self.bulk_worker = BulkIngestWorker(folder_path, debug_mode=self.controller.match_service.debug_mode)
        self.bulk_thread = QThread()
        self.bulk_worker.moveToThread(self.bulk_thread)
        
        self.progress_dlg = IngestionProgressDialog(self)
        self.progress_dlg.setWindowTitle("Bulk Ingestion Running")
        self.progress_dlg.rejected.connect(self.bulk_worker.stop)
        
        self.bulk_thread.started.connect(self.bulk_worker.run)
        self.bulk_worker.progress.connect(self.progress_dlg.append_log)
        self.bulk_worker.result.connect(self._on_bulk_finished)
        self.bulk_worker.finished.connect(self.bulk_thread.quit)
        self.bulk_worker.finished.connect(self.progress_dlg.set_finished)
        self.bulk_worker.finished.connect(self.bulk_worker.deleteLater)
        self.bulk_thread.finished.connect(self.bulk_thread.deleteLater)
        
        self.bulk_thread.start()
        self.progress_dlg.show()
        
    def _on_bulk_finished(self, result):
        if self.progress_dlg:
            self.progress_dlg.close()
        count = result.get("processed", 0)
        QMessageBox.information(self, "Complete", f"Bulk Ingestion finished. Processed {count} items.")
        
        # Switch view to staging automatically
        self.source_combo.setCurrentText("Staging Area")
        self._refresh_loaders()
