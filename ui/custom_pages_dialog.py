from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, QInputDialog, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt
import os

class CustomPagesDialog(QDialog):
    def __init__(self, parent, session_data):
        super().__init__(parent)
        self.session_data = session_data
        if "custom_pages" not in self.session_data:
            self.session_data["custom_pages"] = []
            
        self.setWindowTitle("Manage Custom PDF Pages")
        self.setMinimumSize(400, 300)
        
        layout = QVBoxLayout(self)
        
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        self.refresh_list()
        
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("➕ Add Full Page")
        btn_add.clicked.connect(self.add_page)
        
        btn_remove = QPushButton("❌ Remove Selected")
        btn_remove.clicked.connect(self.remove_page)
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_remove)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
        
    def refresh_list(self):
        self.list_widget.clear()
        for page in self.session_data["custom_pages"]:
            title = page.get("title", "Untitled")
            path = page.get("path", "")
            filename = os.path.basename(path)
            
            item = QListWidgetItem(f"{title} - ({filename})")
            item.setData(Qt.UserRole, page)
            self.list_widget.addItem(item)
            
    def add_page(self):
        title, ok = QInputDialog.getText(self, "Page Title", "Enter a title for this page (optional):")
        if not ok:
            return
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Full Page Image", "", "Image Files (*.png *.jpg *.jpeg)"
        )
        
        if file_path:
            self.session_data["custom_pages"].append({
                "title": title.strip(),
                "path": file_path
            })
            self.refresh_list()
            self.parent().controller.status_updated.emit(f"Added custom page: {title}")
            
    def remove_page(self):
        current_item = self.list_widget.currentItem()
        if not current_item:
            return
            
        page_data = current_item.data(Qt.UserRole)
        if page_data in self.session_data["custom_pages"]:
            self.session_data["custom_pages"].remove(page_data)
            self.refresh_list()
