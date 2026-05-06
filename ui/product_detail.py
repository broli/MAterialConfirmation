from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                QPushButton, QFrame, QScrollArea, QWidget, QSizePolicy, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont
import os

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
        
        footer.addWidget(self.btn_change)
        footer.addWidget(self.btn_confirm)
        footer.addStretch()
        footer.addWidget(btn_close)
        
        self.main_layout.addLayout(footer)
        
        self.load_item(self.idx)

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())

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
        self.clear_layout(self.content_layout)
        
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
                
                # Brand & SKU
                brand_sku = QHBoxLayout()
                lbl_brand = QLabel(f"<b>Brand:</b> {product.get('brand', 'N/A')}")
                lbl_sku = QLabel(f"<b>SKU:</b> {product.get('sku', 'N/A')}")
                brand_sku.addWidget(lbl_brand)
                brand_sku.addSpacing(20)
                brand_sku.addWidget(lbl_sku)
                brand_sku.addStretch()
                scroll_l.addLayout(brand_sku)
                
                # Description
                full_desc = product.get('oneclick_description', 'N/A')
                lbl_full_desc = QLabel(f"<b>Description:</b><br>{full_desc}")
                lbl_full_desc.setWordWrap(True)
                scroll_l.addWidget(lbl_full_desc)
                
                # Printable Details
                printable = product.get('printable', {})
                p_text = f"<b>Finish:</b> {printable.get('finish', 'N/A')}<br>"
                
                dims = printable.get('dimensions', {})
                if dims:
                    dim_str = ", ".join([f"{k}: {v}" for k, v in dims.items()])
                    p_text += f"<b>Dimensions:</b> {dim_str}"
                else:
                    p_text += "<b>Dimensions:</b> N/A"
                
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
