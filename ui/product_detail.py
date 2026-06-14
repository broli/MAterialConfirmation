from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                QPushButton, QFrame, QScrollArea, QWidget, QSizePolicy, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont
import os
from ui.utils import clear_layout
from ui.components.product_form import ProductFormWidget
import copy

class OverrideDialog(QDialog):
    def __init__(self, parent, base_data, current_overrides):
        super().__init__(parent)
        self.setWindowTitle("Override Product Details (Temporary)")
        self.setMinimumSize(600, 700)
        
        self.base_data = base_data
        
        layout = QVBoxLayout(self)
        
        lbl_info = QLabel("<b>Note:</b> Changes made here only affect this specific item for this export. The master database will not be updated.")
        lbl_info.setStyleSheet("color: #ffa726; background: #3e2723; padding: 10px; border-radius: 4px;")
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)
        
        self.form = ProductFormWidget(self, batch_mode=False)
        
        merged_data = copy.deepcopy(base_data)
        if current_overrides:
            def deep_merge(target, updates):
                for k, v in updates.items():
                    if isinstance(v, dict) and isinstance(target.get(k), dict):
                        deep_merge(target[k], v)
                    else:
                        target[k] = v
            deep_merge(merged_data, current_overrides)
            
        self.form.load_data(merged_data)
        
        layout.addWidget(self.form, 1)
        
        footer = QHBoxLayout()
        btn_save = QPushButton("Save Overrides")
        btn_save.setStyleSheet("background-color: #2e7d32; color: white;")
        btn_save.clicked.connect(self.accept)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        footer.addStretch()
        footer.addWidget(btn_save)
        footer.addWidget(btn_cancel)
        layout.addLayout(footer)

    def get_overrides(self):
        new_data, _ = self.form.get_data()
        overrides = {}
        
        for k in ["sku", "brand", "provider", "routing_tag", "oneclick_description"]:
            if new_data.get(k) != self.base_data.get(k):
                overrides[k] = new_data.get(k)
                
        new_printable = new_data.get("printable", {})
        base_printable = self.base_data.get("printable", {})
        
        print_diff = {}
        for k, v in new_printable.items():
            if k not in base_printable or base_printable[k] != v:
                print_diff[k] = v
                
        if print_diff:
            overrides["printable"] = print_diff
            
        return overrides

class ProductDetailDialog(QDialog):
    def __init__(self, parent, start_idx, controller):
        super().__init__(parent)
        self.controller = controller
        self.idx = start_idx
        
        self.setWindowTitle("Product Details & Match Info")
        self.setMinimumSize(700, 600)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(10)
        
        # Navigation header
        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("< Previous")
        self.btn_prev.clicked.connect(self.go_prev)
        nav_layout.addWidget(self.btn_prev)
        
        nav_layout.addStretch()
        self.lbl_index = QLabel("")
        nav_layout.addWidget(self.lbl_index)
        nav_layout.addStretch()
        
        self.btn_next = QPushButton("Next >")
        self.btn_next.clicked.connect(self.go_next)
        nav_layout.addWidget(self.btn_next)
        
        self.main_layout.addLayout(nav_layout)
        
        # Content area
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.content_widget, 1)
        
        # Footer
        footer = QHBoxLayout()
        
        self.btn_change = QPushButton("Change")
        self.btn_change.setFixedWidth(100)
        self.btn_change.setStyleSheet("background-color: #424242; color: white;")
        self.btn_change.clicked.connect(self.on_change)
        
        self.btn_confirm = QPushButton("Confirm")
        self.btn_confirm.setFixedWidth(120)
        self.btn_confirm.clicked.connect(self.on_confirm)
        
        btn_close = QPushButton("Close")
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        
        self.btn_override = QPushButton("Override Details")
        self.btn_override.setFixedWidth(130)
        self.btn_override.setStyleSheet("background-color: #ffa726; color: black; font-weight: bold;")
        self.btn_override.clicked.connect(self.on_override)
        
        footer.addWidget(self.btn_change)
        footer.addWidget(self.btn_override)
        footer.addWidget(self.btn_confirm)
        footer.addStretch()
        footer.addWidget(btn_close)
        
        self.main_layout.addLayout(footer)
        
        self.load_item(self.idx)



    def get_valid_items(self):
        # returns a list of valid indices based on hide_ignored
        items = self.controller.session_data.get("line_items", [])
        hide_ignored = self.parent().hide_ignored_var.isChecked()
        valid = []
        for i, item in enumerate(items):
            is_ignored = item.get("_match", {}).get("is_ignored", False)
            if hide_ignored and is_ignored:
                continue
            valid.append(i)
        return valid

    def go_prev(self):
        valid = self.get_valid_items()
        if self.idx in valid:
            curr = valid.index(self.idx)
            if curr > 0:
                self.load_item(valid[curr-1])
        else:
            # If current is somehow not valid, just find the closest previous valid
            for i in reversed(valid):
                if i < self.idx:
                    self.load_item(i)
                    break

    def go_next(self):
        valid = self.get_valid_items()
        if self.idx in valid:
            curr = valid.index(self.idx)
            if curr < len(valid) - 1:
                self.load_item(valid[curr+1])
        else:
            for i in valid:
                if i > self.idx:
                    self.load_item(i)
                    break

    def on_change(self):
        items = self.controller.session_data.get("line_items", [])
        if 0 <= self.idx < len(items):
            item = items[self.idx]
            if item.get("is_temp"):
                self.parent().edit_temp_item(self.idx)
                self.load_item(self.idx)
            else:
                if self.parent().change_item_match(self.idx):
                    self.load_item(self.idx)

    def on_override(self):
        items = self.controller.session_data.get("line_items", [])
        if 0 <= self.idx < len(items):
            item = items[self.idx]
            match_id = item.get("_match", {}).get("match_id")
            
            if not match_id:
                QMessageBox.warning(self, "No Match", "This item has no database match to override. Please assign a match first.")
                return
                
            db_item = self.controller.find_product_by_id(match_id)
            if not db_item:
                QMessageBox.warning(self, "Error", "Database product not found.")
                return
                
            current_overrides = item.get("overrides", {})
            
            dlg = OverrideDialog(self, db_item, current_overrides)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                new_overrides = dlg.get_overrides()
                if self.controller.update_item_overrides(self.idx, new_overrides):
                    self.load_item(self.idx)

    def on_qty_change(self, delta):
        if self.parent().update_item_qty(self.idx, delta):
            self.load_item(self.idx)

    def on_confirm(self):
        items = self.controller.session_data.get("line_items", [])
        if 0 <= self.idx < len(items):
            item = items[self.idx]
            was_confirmed = item.get("confirmed", False)
            match_id = item.get("_match", {}).get("match_id")
            
            self.parent().toggle_confirm(self.idx, match_id)
            
            # If we just confirmed it, move to next item
            if not was_confirmed:
                self.go_next()
            else:
                self.load_item(self.idx)

    def load_item(self, idx):
        self.idx = idx
        clear_layout(self.content_layout)
        
        items = self.controller.session_data.get("line_items", [])
        if idx < 0 or idx >= len(items):
            return
            
        item_data = items[idx]
        match_data = item_data.get("_match", {})
        
        # update index label and buttons
        valid = self.get_valid_items()
        self.lbl_index.setText(f"Item {idx + 1} of {len(items)}")
        
        if self.idx in valid:
            curr = valid.index(self.idx)
            self.btn_prev.setEnabled(curr > 0)
            self.btn_next.setEnabled(curr < len(valid) - 1)
        else:
            self.btn_prev.setEnabled(any(i < self.idx for i in valid))
            self.btn_next.setEnabled(any(i > self.idx for i in valid))
            
        # Update confirm button
        confirmed = item_data.get("confirmed", False)
        is_ignored = match_data.get("is_ignored", False)
        
        if item_data.get("is_temp"):
            self.btn_change.setText("Edit Temp")
        else:
            self.btn_change.setText("Change")
            
        if item_data.get("confirmed", False):
            btn_color = "#757575" if is_ignored else "#2e7d32"
            self.btn_confirm.setText("Unconfirm")
            self.btn_confirm.setStyleSheet(f"background-color: {btn_color}; color: white; font-size: 16px; font-weight: bold;")
        else:
            self.btn_confirm.setText("Confirm")
            self.btn_confirm.setStyleSheet("background-color: #1565c0; color: white; font-size: 16px; font-weight: bold;")
        self.btn_confirm.setEnabled(True)

        # 1. Raw PDF Info (Tighter)
        raw_group = QFrame()
        raw_group.setStyleSheet("background-color: #1e1e1e; border-left: 4px solid #555; border-radius: 4px;")
        raw_l = QVBoxLayout(raw_group)
        raw_l.setContentsMargins(10, 5, 10, 5)
        raw_l.setSpacing(2)
        
        header_raw = QLabel("📄 CONTRACT INFO (FROM PDF)")
        header_raw.setStyleSheet("color: #aaa; font-size: 10px; font-weight: bold;")
        raw_l.addWidget(header_raw)
        
        raw_desc = item_data.get('raw_description', 'N/A')
        lbl_raw_desc = QLabel(raw_desc)
        lbl_raw_desc.setWordWrap(True)
        lbl_raw_desc.setStyleSheet("font-size: 13px; color: #eee;")
        raw_l.addWidget(lbl_raw_desc)
        
        meta_layout = QHBoxLayout()
        meta_txt = f"<b>Room:</b> {item_data.get('room', 'N/A')} | <b>Qty:</b>"
        lbl_meta = QLabel(meta_txt)
        lbl_meta.setStyleSheet("color: #888; font-size: 11px;")
        meta_layout.addWidget(lbl_meta)
        
        btn_minus = QPushButton("-")
        btn_minus.setFixedSize(22, 22)
        btn_minus.setStyleSheet("background-color: #1976d2; color: white; border-radius: 11px; font-weight: bold; font-size: 14px;")
        btn_minus.clicked.connect(lambda: self.on_qty_change(-1))
        meta_layout.addWidget(btn_minus)
        
        lbl_qty_val = QLabel(f"<b>{item_data.get('qty', 1)}</b>")
        lbl_qty_val.setStyleSheet("color: #eee; font-size: 13px;")
        meta_layout.addWidget(lbl_qty_val)
        
        btn_plus = QPushButton("+")
        btn_plus.setFixedSize(22, 22)
        btn_plus.setStyleSheet("background-color: #1976d2; color: white; border-radius: 11px; font-weight: bold; font-size: 14px;")
        btn_plus.clicked.connect(lambda: self.on_qty_change(1))
        meta_layout.addWidget(btn_plus)
        
        lbl_unit = QLabel(item_data.get('unit', ''))
        lbl_unit.setStyleSheet("color: #888; font-size: 11px;")
        meta_layout.addWidget(lbl_unit)
        meta_layout.addStretch()
        
        raw_l.addLayout(meta_layout)
        
        self.content_layout.addWidget(raw_group)
        
        # 2. Match Info (Scrollable and detailed)
        match_id = match_data.get("match_id")
        confidence = match_data.get("confidence", 0)
        color_hex = match_data.get("color_hex", "#888888")
        
        match_group = QFrame()
        match_group.setStyleSheet(f"background-color: #252525; border-left: 4px solid {color_hex}; border-radius: 4px;")
        match_l = QVBoxLayout(match_group)
        
        header_match = QHBoxLayout()
        lbl_h_match = QLabel("🔗 DATABASE MATCH")
        lbl_h_match.setStyleSheet("color: #aaa; font-size: 10px; font-weight: bold;")
        header_match.addWidget(lbl_h_match)
        
        lbl_conf = QLabel(f"Confidence: {confidence:.1f}%")
        lbl_conf.setStyleSheet(f"color: {color_hex}; font-weight: bold; font-size: 12px;")
        header_match.addStretch()
        header_match.addWidget(lbl_conf)
        match_l.addLayout(header_match)
        
        if match_id:
            product = self.controller.find_product_by_id(match_id)
            if product:
                # Scroll Area for details
                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setFrameShape(QFrame.NoFrame)
                scroll.setStyleSheet("background: transparent;")
                
                scroll_content = QWidget()
                scroll_l = QVBoxLayout(scroll_content)
                scroll_l.setSpacing(8)
                
                # Apply overrides for display
                overrides = item_data.get("overrides", {})
                if overrides:
                    import copy
                    product = copy.deepcopy(product)
                    def deep_merge(target, updates):
                        for k, v in updates.items():
                            if isinstance(v, dict) and isinstance(target.get(k), dict):
                                deep_merge(target[k], v)
                            else:
                                target[k] = v
                    deep_merge(product, overrides)
                    
                    lbl_warn = QLabel("⚠️ Displaying temporary overrides for this item")
                    lbl_warn.setStyleSheet("color: #ffa726; font-weight: bold; font-size: 11px;")
                    scroll_l.addWidget(lbl_warn)
                
                # Brand & SKU
                brand_sku = QHBoxLayout()
                b_color = "#ffa726" if "brand" in overrides else "white"
                s_color = "#ffa726" if "sku" in overrides else "white"
                lbl_brand = QLabel(f"<b style='color:{b_color}'>Brand:</b> <span style='color:{b_color}'>{product.get('brand', 'N/A')}</span>")
                lbl_sku = QLabel(f"<b style='color:{s_color}'>SKU:</b> <span style='color:{s_color}'>{product.get('sku', 'N/A')}</span>")
                brand_sku.addWidget(lbl_brand)
                brand_sku.addSpacing(20)
                brand_sku.addWidget(lbl_sku)
                brand_sku.addStretch()
                scroll_l.addLayout(brand_sku)
                
                # Description
                full_desc = product.get('oneclick_description', 'N/A')
                d_color = "#ffa726" if "oneclick_description" in overrides else "white"
                lbl_full_desc = QLabel(f"<b style='color:{d_color}'>Description:</b><br><span style='color:{d_color}'>{full_desc}</span>")
                lbl_full_desc.setWordWrap(True)
                scroll_l.addWidget(lbl_full_desc)
                
                # Printable Details
                printable = product.get('printable', {})
                print_overrides = overrides.get("printable", {})
                
                f_color = "#ffa726" if "finish" in print_overrides else "white"
                p_text = f"<b>Finish:</b> <span style='color:{f_color}'>{printable.get('finish', 'N/A')}</span><br>"
                
                dims = printable.get('dimensions', {})
                d_color = "#ffa726" if "dimensions" in print_overrides else "white"
                if dims:
                    dim_str = ", ".join([f"{k}: {v}" for k, v in dims.items()])
                    p_text += f"<b>Dimensions:</b> <span style='color:{d_color}'>{dim_str}</span>"
                else:
                    p_text += f"<b>Dimensions:</b> <span style='color:{d_color}'>N/A</span>"

                
                lbl_printable = QLabel(p_text)
                lbl_printable.setStyleSheet("background-color: #333; padding: 5px; border-radius: 3px;")
                scroll_l.addWidget(lbl_printable)
                
                # Tag
                lbl_tag = QLabel(f"<b>Routing Tag:</b> {product.get('routing_tag', 'N/A')}")
                lbl_tag.setStyleSheet("color: #64b5f6;")
                scroll_l.addWidget(lbl_tag)
                
                # Image Preview
                img_file = printable.get("image_file")
                if img_file:
                    full_path = os.path.join("database", "assets", img_file)
                    if os.path.exists(full_path):
                        img_lbl = QLabel()
                        pixmap = QPixmap(full_path)
                        if not pixmap.isNull():
                            img_lbl.setPixmap(pixmap.scaled(500, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                            img_lbl.setAlignment(Qt.AlignCenter)
                            img_lbl.setStyleSheet("margin-top: 10px; border: 1px solid #444;")
                            scroll_l.addWidget(img_lbl)
                        else:
                            scroll_l.addWidget(QLabel(f"<i>(Failed to load image: {img_file})</i>"))
                
                scroll_l.addStretch()
                scroll.setWidget(scroll_content)
                match_l.addWidget(scroll)
            else:
                match_l.addWidget(QLabel(f"Match ID '{match_id}' found in metadata, but missing from current catalog."))
        else:
            match_l.addWidget(QLabel("No database match found for this item."))
            
        self.content_layout.addWidget(match_group, 1)
