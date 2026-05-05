from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                QPushButton, QFrame, QScrollArea, QWidget, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont
import os

class ProductDetailDialog(QDialog):
    def __init__(self, parent, item_data, match_data, controller):
        super().__init__(parent)
        self.item_data = item_data
        self.match_data = match_data
        self.controller = controller
        
        self.setWindowTitle("Product Details & Match Info")
        self.setMinimumSize(700, 600)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        
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
        
        meta_txt = f"<b>Room:</b> {item_data.get('room', 'N/A')} | <b>Qty:</b> {item_data.get('qty', 1)} {item_data.get('unit', '')}"
        lbl_meta = QLabel(meta_txt)
        lbl_meta.setStyleSheet("color: #888; font-size: 11px;")
        raw_l.addWidget(lbl_meta)
        
        main_layout.addWidget(raw_group)
        
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
            
        main_layout.addWidget(match_group, 1)
        
        # Footer
        footer = QHBoxLayout()
        btn_close = QPushButton("Close")
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        footer.addStretch()
        footer.addWidget(btn_close)
        main_layout.addLayout(footer)

