import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QComboBox, 
                               QPushButton, QFrame, QFileDialog, QScrollArea, QGroupBox, QGridLayout, QCheckBox)
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
    def __init__(self, parent=None, categories_path="database/categories", batch_mode=False, dropdown_categories_path=None):
        super().__init__(parent)
        self.categories_path = categories_path
        self.dropdown_categories_path = dropdown_categories_path or categories_path
        self.batch_mode = batch_mode
        self.dim_rows = []
        self._build_ui()

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
        
        def add_core_field(row, label_text, widget, attr_prefix, is_unique=False):
            if self.batch_mode and is_unique:
                widget.hide()
                return
            if self.batch_mode:
                cb = QCheckBox(label_text)
                setattr(self, f"{attr_prefix}_cb", cb)
                core_layout.addWidget(cb, row, 0)
                if isinstance(widget, QLineEdit):
                    widget.textChanged.connect(lambda text, c=cb: c.setChecked(True))
                elif isinstance(widget, QComboBox):
                    widget.currentIndexChanged.connect(lambda idx, c=cb: c.setChecked(True))
                    if widget.isEditable():
                        widget.editTextChanged.connect(lambda text, c=cb: c.setChecked(True))
            else:
                lbl = QLabel(label_text)
                setattr(self, f"{attr_prefix}_lbl", lbl)
                core_layout.addWidget(lbl, row, 0)
            core_layout.addWidget(widget, row, 1)

        self.id_entry = QLineEdit()
        add_core_field(0, "ID *", self.id_entry, "id", is_unique=True)
        
        self.sku_entry = QLineEdit()
        add_core_field(1, "SKU *", self.sku_entry, "sku")
        
        self.brand_entry = QLineEdit()
        add_core_field(2, "Brand *", self.brand_entry, "brand")
        
        self.provider_entry = QLineEdit()
        add_core_field(3, "Provider", self.provider_entry, "provider")
        
        self.purchase_link_entry = QLineEdit()
        add_core_field(4, "Purchase Link", self.purchase_link_entry, "purchase_link")
        
        self.oneclick_entry = QLineEdit()
        add_core_field(5, "OneClick Desc *", self.oneclick_entry, "oneclick", is_unique=True)
        
        self.routing_entry = QComboBox()
        self.routing_entry.addItems(["WAREHOUSE", "PROCURE", "WH_OR_PROCURE", "IGNORE"])
        add_core_field(6, "Routing Tag *", self.routing_entry, "routing")
        
        self.cat_entry = QComboBox()
        self.cat_entry.setEditable(True)
        self.cat_entry.addItems(self._get_existing_categories())
        self.cat_entry.currentIndexChanged.connect(self._on_category_changed)
        self.cat_entry.editTextChanged.connect(lambda: self._on_category_changed(-1))
        add_core_field(7, "Category File *", self.cat_entry, "cat")
        
        core_group.setLayout(core_layout)
        layout.addWidget(core_group)
        
        # --- Printable Fields ---
        print_group = QGroupBox("Printable Output (Client Facing)")
        print_layout = QVBoxLayout()
        
        f_layout = QHBoxLayout()
        if self.batch_mode:
            self.finish_cb = QCheckBox("Finish:")
            f_layout.addWidget(self.finish_cb)
            self.finish_entry = QLineEdit()
            self.finish_entry.textChanged.connect(lambda t: self.finish_cb.setChecked(True))
            f_layout.addWidget(self.finish_entry)
        else:
            f_layout.addWidget(QLabel("Finish:"))
            self.finish_entry = QLineEdit()
            f_layout.addWidget(self.finish_entry)
        print_layout.addLayout(f_layout)
        
        d_layout = QHBoxLayout()
        if self.batch_mode:
            self.desc_cb = QCheckBox("Description:")
            d_layout.addWidget(self.desc_cb)
            self.desc_entry = QLineEdit()
            self.desc_entry.textChanged.connect(lambda t: self.desc_cb.setChecked(True))
            d_layout.addWidget(self.desc_entry)
        else:
            d_layout.addWidget(QLabel("Description:"))
            self.desc_entry = QLineEdit()
            d_layout.addWidget(self.desc_entry)
        print_layout.addLayout(d_layout)
        
        # Dimensions
        self.dims_container = QVBoxLayout()
        if self.batch_mode:
            self.dims_cb = QCheckBox("Dimensions (Overwrite All):")
            print_layout.addWidget(self.dims_cb)
        else:
            print_layout.addWidget(QLabel("Dimensions:"))
        print_layout.addLayout(self.dims_container)
        
        btn_add_dim = QPushButton("+ Add Dimension")
        btn_add_dim.clicked.connect(lambda: self.add_dimension_row())
        print_layout.addWidget(btn_add_dim)
        
        # Image
        if not self.batch_mode:
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
        else:
            self.image_entry = QLineEdit()
            self.image_preview_label = QLabel()
            
        print_group.setLayout(print_layout)
        layout.addWidget(print_group)
        
        layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _get_existing_categories(self):
        if not os.path.exists(self.dropdown_categories_path): return []
        return [f for f in os.listdir(self.dropdown_categories_path) if f.endswith('.yaml')]

    def _on_category_changed(self, index):
        # Auto-fill ID if empty when category changes
        if not self.id_entry.text().strip():
            cat_file = self.cat_entry.currentText().strip()
            if not cat_file: return
            
            from models.product_service import ProductService
            next_id = ProductService.get_next_id(cat_file, self.dropdown_categories_path)
            self.id_entry.setText(next_id)

    def add_dimension_row(self, key="", value=""):
        row = DimensionRow(key, value)
        row.remove_requested.connect(self._remove_dimension_row)
        if self.batch_mode and hasattr(self, 'dims_cb'):
            self.dims_cb.setChecked(True)
            row.key_edit.textChanged.connect(lambda t: self.dims_cb.setChecked(True))
            row.value_edit.textChanged.connect(lambda t: self.dims_cb.setChecked(True))
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
            if isinstance(dims, str):
                dims_str = dims.strip()
                if not dims_str:
                    dims = {}
                else:
                    import ast
                    try:
                        dims = ast.literal_eval(dims_str)
                        if not isinstance(dims, dict):
                            dims = {"raw": str(dims)}
                    except Exception:
                        dims = {"raw": dims_str}
                    
            if isinstance(dims, dict):
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
        data = {}
        
        def _get_if_active(attr_prefix):
            if not self.batch_mode: return True
            cb = getattr(self, f"{attr_prefix}_cb", None)
            return cb and cb.isChecked()

        if _get_if_active("id"): data["id"] = self.id_entry.text().strip()
        if _get_if_active("sku"): data["sku"] = self.sku_entry.text().strip()
        if _get_if_active("brand"): data["brand"] = self.brand_entry.text().strip()
        if _get_if_active("provider"): data["provider"] = self.provider_entry.text().strip()
        if _get_if_active("routing"): data["routing_tag"] = self.routing_entry.currentText()
        if _get_if_active("purchase_link"): data["purchase_link"] = self.purchase_link_entry.text().strip()
        if _get_if_active("oneclick"): data["oneclick_description"] = self.oneclick_entry.text().strip()
        
        # Printable data
        printable_updates = {}
        
        if _get_if_active("finish"): printable_updates["finish"] = self.finish_entry.text().strip()
        if _get_if_active("desc"): printable_updates["description"] = self.desc_entry.text().strip()
        if not self.batch_mode: printable_updates["image_file"] = self.image_entry.text().strip()
        
        if not self.batch_mode or (hasattr(self, 'dims_cb') and self.dims_cb.isChecked()):
            dims = {}
            for row in self.dim_rows:
                res = row.get_data()
                if res:
                    dims[res[0]] = res[1]
            # In batch mode, we explicitly set dims (even if empty to wipe it), or if not empty
            if not self.batch_mode or self.dims_cb.isChecked():
                printable_updates["dimensions"] = dims
            
        if printable_updates:
            data["printable"] = printable_updates
            
        return data, self.cat_entry.currentText() if _get_if_active("cat") else None
