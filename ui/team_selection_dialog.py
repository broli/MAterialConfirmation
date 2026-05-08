import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                             QHBoxLayout, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from models.config_manager import ConfigManager

class TeamSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to PKB SMS")
        self.setFixedSize(500, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Select Your Team")
        title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Please choose your team to automatically configure the database settings.")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #aaaaaa;")
        layout.addWidget(subtitle)
        
        # Team Buttons Container
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(15)
        
        for team_name in ConfigManager.TEAM_PRESETS.keys():
            btn = QPushButton(team_name)
            btn.setFixedHeight(60)
            btn.setFont(QFont("Segoe UI", 14))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3d3d3d;
                    border: 2px solid #555555;
                    border-radius: 10px;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #4d4d4d;
                    border-color: #0078d4;
                }
                QPushButton:pressed {
                    background-color: #2d2d2d;
                }
            """)
            btn.clicked.connect(lambda checked=False, name=team_name: self.select_team(name))
            buttons_layout.addWidget(btn)
            
        layout.addLayout(buttons_layout)
        
        # Spacer
        layout.addStretch()
        
        # Footer
        footer = QHBoxLayout()
        manual_btn = QPushButton("Advanced / Manual Setup")
        manual_btn.setFlat(True)
        manual_btn.setStyleSheet("color: #0078d4; text-decoration: underline;")
        manual_btn.setCursor(Qt.PointingHandCursor)
        manual_btn.clicked.connect(self.manual_setup)
        footer.addStretch()
        footer.addWidget(manual_btn)
        footer.addStretch()
        layout.addLayout(footer)

    def select_team(self, team_name):
        ConfigManager.apply_preset(team_name)
        self.accept()
        
    def manual_setup(self):
        # Just close and let them handle it via Settings UI later or create empty settings
        ConfigManager.save(ConfigManager.DEFAULT_SETTINGS)
        self.accept()
