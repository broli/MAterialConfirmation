import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QComboBox, 
                               QPushButton, QFrame, QFileDialog, QScrollArea, QGroupBox, QGridLayout)
from PySide6.QtCore import Qt, Signal

class DimensionRow(QWidget):
    remove_requested = Signal(QWidget)

    def __init__(self, key="", value="", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.key_edit = QLineEdit(key)
        self.key_edit.setPlaceholderText("e.g. width")
        self.key_edit.setMaximumWidth(100)
        
        self.value_edit = QLineEdit(value)
        self.value_edit.setPlaceholderText("e.g. 30\"")
        
        self.btn_remove = QPushButton("X")
        self.btn_remove.setStyleSheet("background-color: #d32f2f; color: white; max-width: 30px;")
        self.btn_remove.clicked.connect(lambda: self.remove_requested.emit(self))
        
        layout.addWidget(self.key_edit)
        layout.addWidget(self.value_edit)
        layout.addWidget(self.btn_remove)

    def get_data(self):
        k = self.key_edit.text().strip()
        v = self.value_edit.text().strip()
        if k and v:
            return k, v
        return None

class ProductFormWidget(QWidget):
    def __init__(self, parent=None, categories_path="database/categories"):
        super().__init__(parent)
        self.categories_path = categories_path
        self._build_ui()
        self.dim_rows = []

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        
        # --- Core Fields ---
        core_group = QGroupBox("Core Information")
        core_layout = QGridLayout()
        
        core_layout.addWidget(QLabel("ID *"), 0, 0)
        self.id_entry = QLineEdit()
        core_layout.addWidget(self.id_entry, 0, 1)
        
        core_layout.addWidget(QLabel("SKU *"), 1, 0)
        self.sku_entry = QLineEdit()
        core_layout.addWidget(self.sku_entry, 1, 1)
        
        core_layout.addWidget(QLabel("Brand *"), 2, 0)
        self.brand_entry = QLineEdit()
        core_layout.addWidget(self.brand_entry, 2, 1)
        
        core_layout.addWidget(QLabel("Provider"), 3, 0)
        self.provider_entry = QLineEdit()
        core_layout.addWidget(self.provider_entry, 3, 1)
        
        core_layout.addWidget(QLabel("Purchase Link"), 4, 0)
        self.purchase_link_entry = QLineEdit()
        core_layout.addWidget(self.purchase_link_entry, 4, 1)
        
        core_layout.addWidget(QLabel("OneClick Desc *"), 5, 0)
        self.oneclick_entry = QLineEdit()
        core_layout.addWidget(self.oneclick_entry, 5, 1)
        
        # Dropdowns
        core_layout.addWidget(QLabel("Routing Tag *"), 6, 0)
        self.routing_entry = QComboBox()
        self.routing_entry.addItems(["WAREHOUSE", "PROCURE", "WH_OR_PROCURE", "IGNORE"])
        core_layout.addWidget(self.routing_entry, 6, 1)
        
        core_layout.addWidget(QLabel("Category File *"), 7, 0)
        self.cat_entry = QComboBox()
        self.cat_entry.addItems(self._get_existing_categories())
        self.cat_entry.currentIndexChanged.connect(self._on_category_changed)
        core_layout.addWidget(self.cat_entry, 7, 1)
        
        core_group.setLayout(core_layout)
        layout.addWidget(core_group)
        
        # --- Printable Fields ---
        print_group = QGroupBox("Printable Output (Client Facing)")
        print_layout = QVBoxLayout()
        
        f_layout = QHBoxLayout()
        f_layout.addWidget(QLabel("Finish:"))
        self.finish_entry = QLineEdit()
        f_layout.addWidget(self.finish_entry)
        print_layout.addLayout(f_layout)
        
        d_layout = QHBoxLayout()
        d_layout.addWidget(QLabel("Description:"))
        self.desc_entry = QLineEdit()
        d_layout.addWidget(self.desc_entry)
        print_layout.addLayout(d_layout)
        
        # Dimensions
        self.dims_container = QVBoxLayout()
        print_layout.addWidget(QLabel("Dimensions:"))
        print_layout.addLayout(self.dims_container)
        
        btn_add_dim = QPushButton("+ Add Dimension")
        btn_add_dim.clicked.connect(lambda: self.add_dimension_row())
        print_layout.addWidget(btn_add_dim)
        
        # Image
        img_layout = QHBoxLayout()
        img_layout.addWidget(QLabel("Image File:"))
        self.image_entry = QLineEdit()
        img_layout.addWidget(self.image_entry)
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self._browse_image)
        img_layout.addWidget(btn_browse)
        print_layout.addLayout(img_layout)
        
        # Image Preview
        self.image_preview_label = QLabel("No Image")
        self.image_preview_label.setAlignment(Qt.AlignCenter)
        self.image_preview_label.setStyleSheet("border: 1px dashed #555; background-color: #1e1e1e; color: #888;")
        self.image_preview_label.setFixedSize(150, 150)
        
        preview_layout = QHBoxLayout()
        preview_layout.addWidget(self.image_preview_label)
        preview_layout.addStretch()
        print_layout.addLayout(preview_layout)
        
        print_group.setLayout(print_layout)
        layout.addWidget(print_group)
        
        layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _get_existing_categories(self):
        if not os.path.exists(self.categories_path): return []
        return [f for f in os.listdir(self.categories_path) if f.endswith('.yaml')]

    def _on_category_changed(self, index):
        # Auto-fill ID if empty when category changes
        if not self.id_entry.text().strip():
            cat_file = self.cat_entry.currentText()
            from models.product_service import ProductService
            next_id = ProductService.get_next_id(cat_file, self.categories_path)
            self.id_entry.setText(next_id)

    def add_dimension_row(self, key="", value=""):
        row = DimensionRow(key, value)
        row.remove_requested.connect(self._remove_dimension_row)
        self.dims_container.addWidget(row)
        self.dim_rows.append(row)

    def _remove_dimension_row(self, row_widget):
        self.dims_container.removeWidget(row_widget)
        row_widget.deleteLater()
        if row_widget in self.dim_rows:
            self.dim_rows.remove(row_widget)

    def _update_image_preview(self, path):
        from PySide6.QtGui import QPixmap
        
        if not path:
            self.image_preview_label.clear()
            self.image_preview_label.setText("No Image")
            return
            
        if not os.path.isabs(path):
            assets_path = os.path.join(os.path.dirname(self.categories_path), "assets")
            full_path = os.path.join(assets_path, path)
        else:
            full_path = path
            
        if os.path.exists(full_path):
            pixmap = QPixmap(full_path)
            if not pixmap.isNull():
                self.image_preview_label.setPixmap(pixmap.scaled(self.image_preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                return
                
        self.image_preview_label.clear()
        self.image_preview_label.setText("Image not found")

    def _browse_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if path:
            abs_path = os.path.abspath(path)
            self.image_entry.setText(abs_path) # Store absolute path temporarily before save
            self._update_image_preview(abs_path)

    def load_data(self, data: dict, category: str = ""):
        self.id_entry.setText(str(data.get("id", "")))
        self.sku_entry.setText(str(data.get("sku", "")))
        self.brand_entry.setText(str(data.get("brand", "")))
        self.provider_entry.setText(str(data.get("provider", "")))
        self.purchase_link_entry.setText(str(data.get("purchase_link", "")))
        self.oneclick_entry.setText(str(data.get("oneclick_description", "")))
        
        routing = data.get("routing_tag", "WAREHOUSE")
        idx = self.routing_entry.findText(routing)
        if idx >= 0: self.routing_entry.setCurrentIndex(idx)
        
        if category:
            cat_file = category if category.endswith(".yaml") else f"{category}.yaml"
            idx = self.cat_entry.findText(cat_file)
            if idx >= 0: self.cat_entry.setCurrentIndex(idx)
        
        # Printable
        printable = data.get("printable", {})
        if printable:
            self.finish_entry.setText(str(printable.get("finish", "")))
            self.desc_entry.setText(str(printable.get("description", "")))
            
            img_file = str(printable.get("image_file", ""))
            self.image_entry.setText(img_file)
            self._update_image_preview(img_file)
            
            # Clear old dims
            for row in list(self.dim_rows):
                self._remove_dimension_row(row)
                
            dims = printable.get("dimensions", {})
            for k, v in dims.items():
                self.add_dimension_row(k, str(v))
        else:
            self.finish_entry.clear()
            self.desc_entry.clear()
            self.image_entry.clear()
            self._update_image_preview("")
            for row in list(self.dim_rows):
                self._remove_dimension_row(row)

    def get_data(self):
        data = {
            "id": self.id_entry.text().strip(),
            "sku": self.sku_entry.text().strip(),
            "brand": self.brand_entry.text().strip(),
            "provider": self.provider_entry.text().strip(),
            "routing_tag": self.routing_entry.currentText(),
            "purchase_link": self.purchase_link_entry.text().strip(),
            "oneclick_description": self.oneclick_entry.text().strip(),
        }
        
        # Printable data
        finish = self.finish_entry.text().strip()
        desc = self.desc_entry.text().strip()
        img = self.image_entry.text().strip()
        
        dims = {}
        for row in self.dim_rows:
            res = row.get_data()
            if res:
                dims[res[0]] = res[1]
                
        # Only include printable if there's actual data
        if finish or desc or img or dims:
            data["printable"] = {
                "finish": finish,
                "description": desc,
                "dimensions": dims,
                "image_file": img # This could be absolute path if browsed, handled by ProductService
            }
            
        return data, self.cat_entry.currentText()
