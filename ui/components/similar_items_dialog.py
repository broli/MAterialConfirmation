import difflib
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QScrollArea, QWidget, QFrame)
from PySide6.QtCore import Qt

class SimilarItemsDialog(QDialog):
    def __init__(self, parent, staging_item, match_engine, catalog):
        super().__init__(parent)
        self.setWindowTitle("Find Similar Items (Deduplication)")
        self.resize(800, 600)
        
        self.staging_item = staging_item
        self.match_engine = match_engine
        self.catalog = catalog
        self.selected_production_id = None
        
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        desc_label = QLabel("<b>Staging Item:</b>")
        layout.addWidget(desc_label)
        
        target_desc = self.staging_item.get("oneclick_description", "")
        staging_desc_lbl = QLabel(target_desc)
        staging_desc_lbl.setWordWrap(True)
        staging_desc_lbl.setStyleSheet("background-color: #2c2c2c; padding: 10px; border-radius: 5px;")
        layout.addWidget(staging_desc_lbl)
        
        results = self.match_engine.fast_match(target_desc)
        
        if not results:
            layout.addWidget(QLabel("No similar items found in production."))
            btn_close = QPushButton("Close")
            btn_close.clicked.connect(self.reject)
            layout.addWidget(btn_close)
            return
            
        layout.addWidget(QLabel("<b>Top Production Matches:</b>"))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        for score, prod_id, prod_desc in results:
            prod_item = self.catalog.get(prod_id, {})
            
            frame = QFrame()
            frame.setFrameShape(QFrame.StyledPanel)
            frame.setStyleSheet("background-color: #1e1e1e; border-radius: 5px;")
            frame_layout = QVBoxLayout(frame)
            
            header = QHBoxLayout()
            score_lbl = QLabel(f"Score: {score:.1f}%")
            if score >= 90:
                score_lbl.setStyleSheet("color: #4caf50; font-weight: bold;")
            elif score >= 70:
                score_lbl.setStyleSheet("color: #ffeb3b; font-weight: bold;")
            else:
                score_lbl.setStyleSheet("color: #f44336; font-weight: bold;")
                
            header.addWidget(QLabel(f"<b>ID: {prod_id}</b> | Category: {prod_item.get('category_file', 'Unknown')}"))
            header.addStretch()
            header.addWidget(score_lbl)
            frame_layout.addLayout(header)
            
            diff_html = self._generate_diff_html(prod_desc, target_desc)
            diff_lbl = QLabel(diff_html)
            diff_lbl.setWordWrap(True)
            diff_lbl.setTextFormat(Qt.RichText)
            diff_lbl.setStyleSheet("background-color: #121212; padding: 8px; font-family: monospace;")
            frame_layout.addWidget(diff_lbl)
            
            btn_link = QPushButton("Link as Alias (Discard Staging)")
            btn_link.setStyleSheet("background-color: #1976d2; color: white; padding: 5px;")
            btn_link.clicked.connect(lambda checked, pid=prod_id: self._on_link_clicked(pid))
            frame_layout.addWidget(btn_link)
            
            scroll_layout.addWidget(frame)
            
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        layout.addWidget(btn_cancel)

    def _generate_diff_html(self, a_text, b_text):
        """Generates HTML showing the difference between a_text (production) and b_text (staging)."""
        sm = difflib.SequenceMatcher(None, a_text.split(), b_text.split())
        html = []
        for opcode, a0, a1, b0, b1 in sm.get_opcodes():
            if opcode == 'equal':
                html.append(" ".join(a_text.split()[a0:a1]))
            elif opcode == 'insert':
                html.append(f"<span style='color: #4caf50; font-weight: bold;'>{' '.join(b_text.split()[b0:b1])}</span>")
            elif opcode == 'delete':
                html.append(f"<span style='color: #f44336; text-decoration: line-through;'>{' '.join(a_text.split()[a0:a1])}</span>")
            elif opcode == 'replace':
                html.append(f"<span style='color: #f44336; text-decoration: line-through;'>{' '.join(a_text.split()[a0:a1])}</span> <span style='color: #4caf50; font-weight: bold;'>{' '.join(b_text.split()[b0:b1])}</span>")
        return " ".join(html)

    def _on_link_clicked(self, prod_id):
        self.selected_production_id = prod_id
        self.accept()
