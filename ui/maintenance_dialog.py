import os
import shutil
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QScrollArea, QWidget, QFrame, QMessageBox, QListWidget)
from PySide6.QtCore import Qt

class MaintenanceDialog(QDialog):
    def __init__(self, parent, controller, product_service):
        super().__init__(parent)
        self.setWindowTitle("Database Maintenance")
        self.resize(600, 400)
        
        self.controller = controller
        self.product_service = product_service
        self.catalog = self.controller.catalog
        self.match_engine = self.controller.match_service._engine
        
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        lbl_info = QLabel("<b>Select a Maintenance Task</b>")
        layout.addWidget(lbl_info)
        
        btn_assets = QPushButton("🗑️ Clean Unused Assets")
        btn_assets.setStyleSheet("padding: 10px; font-weight: bold;")
        btn_assets.clicked.connect(self._clean_assets)
        layout.addWidget(btn_assets)
        
        btn_dedupe = QPushButton("🔍 Find Database Duplicates")
        btn_dedupe.setStyleSheet("padding: 10px; font-weight: bold;")
        btn_dedupe.clicked.connect(self._find_duplicates)
        layout.addWidget(btn_dedupe)
        
        btn_clean_aliases = QPushButton("🧹 Clean Duplicate Aliases")
        btn_clean_aliases.setStyleSheet("padding: 10px; font-weight: bold;")
        btn_clean_aliases.clicked.connect(self._clean_duplicate_aliases)
        layout.addWidget(btn_clean_aliases)
        
        layout.addStretch()
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _clean_assets(self):
        from models.config_manager import ConfigManager
        
        assets_dir = os.path.join("database", "assets")
        if not os.path.exists(assets_dir):
            QMessageBox.information(self, "Info", "Assets directory not found.")
            return
            
        all_files = set(os.listdir(assets_dir))
        used_files = set()
        
        for item in self.catalog.values():
            img = item.get("printable", {}).get("image_file", "").strip()
            if img:
                used_files.add(img)
                
        cover_filename = ConfigManager.get("cover_image_filename")
        if cover_filename:
            used_files.add(cover_filename)
        else:
            used_files.add("Bath Document Cover Page.png")
                
        unused_files = all_files - used_files
        
        if not unused_files:
            QMessageBox.information(self, "Result", "No unused assets found! Your database is clean.")
            return
            
        reply = QMessageBox.question(self, "Unused Assets Found", 
                                     f"Found {len(unused_files)} unused image files.\nWould you like to delete them permanently?",
                                     QMessageBox.Yes | QMessageBox.No)
                                     
        if reply == QMessageBox.Yes:
            deleted = 0
            for f in unused_files:
                try:
                    os.remove(os.path.join(assets_dir, f))
                    deleted += 1
                except:
                    pass
            QMessageBox.information(self, "Success", f"Deleted {deleted} files.")

    def _find_duplicates(self):
        from ui.components.similar_items_dialog import SimilarItemsDialog
        
        # Build list of potential duplicates
        duplicates = []
        seen_pairs = set()
        
        for item_id, item_data in self.catalog.items():
            desc = item_data.get("oneclick_description", "")
            if not desc: continue
            
            results = self.match_engine.fast_match(desc)
            for score, target_id, _ in results:
                if score >= 90 and target_id != item_id:
                    # Create normalized pair key to avoid A->B and B->A
                    pair = tuple(sorted([item_id, target_id]))
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        duplicates.append((score, item_id, target_id))
        
        # Filter out ids that might not be in the catalog (e.g. stale index)
        valid_duplicates = []
        for score, id1, id2 in duplicates:
            if id1 in self.catalog and id2 in self.catalog:
                valid_duplicates.append((score, id1, id2))
                
        # Sort them once
        valid_duplicates.sort(key=lambda x: x[0], reverse=True)

        if not valid_duplicates:
            QMessageBox.information(self, "Result", "No duplicates found with >90% similarity!")
            return
            
        # Show list of duplicates
        dlg = QDialog(self)
        dlg.setWindowTitle("Potential Duplicates Found")
        dlg.resize(700, 500)
        d_layout = QVBoxLayout(dlg)
        d_layout.addWidget(QLabel(f"Found {len(valid_duplicates)} highly similar pairs. Select one to review and merge."))
        
        list_widget = QListWidget()
        for score, id1, id2 in valid_duplicates:
            cat1 = self.catalog[id1].get("category_file", "")
            cat2 = self.catalog[id2].get("category_file", "")
            list_widget.addItem(f"{score:.1f}% | {id1} ({cat1}) <---> {id2} ({cat2})")
            
        d_layout.addWidget(list_widget)
        
        btn_review = QPushButton("Review Selected")
        def _review(*args):
            idx = list_widget.currentRow()
            if idx < 0: return
            
            score, id1, id2 = valid_duplicates[idx]
            item1 = self.catalog[id1]
            # Open SimilarItemsDialog treating item1 as "Staging" and the rest as "Production"
            sim_dlg = SimilarItemsDialog(dlg, item1, self.match_engine, self.catalog)
            if sim_dlg.exec():
                prod_id = sim_dlg.selected_production_id
                if prod_id and prod_id != id1:
                    # User wants to merge item1 into prod_id
                    prod_item = self.catalog.get(prod_id)
                    
                    aliases = prod_item.get("aliases", [])
                    if not isinstance(aliases, list): aliases = []
                    desc1 = item1.get("oneclick_description", "").strip()
                    if desc1 and desc1 not in aliases:
                        aliases.append(desc1)
                        prod_item["aliases"] = aliases
                        
                        # Save prod
                        cat_file = prod_item.get("category_file", "UNKNOWN.yaml")
                        if not cat_file.endswith(".yaml"): cat_file += ".yaml"
                        self.product_service.upsert_to_yaml(prod_item, cat_file, os.path.join("database", "categories"), os.path.join("database", "assets"))
                        
                    # Delete item1
                    cat1 = item1.get("category_file", "UNKNOWN.yaml")
                    if not cat1.endswith(".yaml"): cat1 += ".yaml"
                    self.product_service.remove_from_yaml(item1.get("id"), cat1, os.path.join("database", "categories"))
                    
                    if id1 in self.catalog:
                        del self.catalog[id1]
                    
                    QMessageBox.information(dlg, "Success", f"Merged {id1} into {prod_id} as alias.")
                    dlg.accept() # Close the list dialog so user can refresh
                    
        btn_review.clicked.connect(_review)
        list_widget.itemDoubleClicked.connect(_review)
        d_layout.addWidget(btn_review)
        
        btn_close = QPushButton("Cancel")
        btn_close.clicked.connect(dlg.reject)
        d_layout.addWidget(btn_close)
        
        dlg.exec()

    def _clean_duplicate_aliases(self):
        items_with_duplicates = []
        for item_id, item_data in self.catalog.items():
            aliases = item_data.get("aliases", [])
            oneclick = item_data.get("oneclick_description", "")
            
            if not isinstance(aliases, list):
                continue
                
            seen = set()
            duplicates = set()
            
            if oneclick:
                seen.add(oneclick)
                
            for a in aliases:
                a_str = str(a)
                if a_str in seen:
                    duplicates.add(a_str)
                seen.add(a_str)
                
            if duplicates:
                items_with_duplicates.append((item_id, item_data, list(duplicates)))
                
        if not items_with_duplicates:
            QMessageBox.information(self, "Result", "No items with duplicate aliases found!")
            return
            
        dlg = QDialog(self)
        dlg.setWindowTitle("Items with Duplicate Aliases")
        dlg.resize(700, 500)
        d_layout = QVBoxLayout(dlg)
        d_layout.addWidget(QLabel(f"Found {len(items_with_duplicates)} items with duplicated aliases. Select one to automatically remove duplicates."))
        
        list_widget = QListWidget()
        for item_id, item_data, dups in items_with_duplicates:
            cat = item_data.get("category_file", "")
            dup_str = ", ".join(dups)
            list_widget.addItem(f"{item_id} ({cat}) - Duplicates: {dup_str}")
            
        d_layout.addWidget(list_widget)
        
        btn_review = QPushButton("Remove Duplicates for Selected")
        def _review(*args):
            idx = list_widget.currentRow()
            if idx < 0: return
            
            item_id, item_data, dups = items_with_duplicates[idx]
            
            aliases = item_data.get("aliases", [])
            oneclick = item_data.get("oneclick_description", "")
            
            new_aliases = []
            seen = set()
            if oneclick:
                seen.add(oneclick)
                
            for a in aliases:
                a_str = str(a)
                if a_str not in seen:
                    new_aliases.append(a)
                    seen.add(a_str)
                    
            item_data["aliases"] = new_aliases
            
            cat_file = item_data.get("category_file", "UNKNOWN.yaml")
            if not cat_file.endswith(".yaml"): cat_file += ".yaml"
            self.product_service.upsert_to_yaml(item_data, cat_file, os.path.join("database", "categories"), os.path.join("database", "assets"))
            
            QMessageBox.information(dlg, "Success", f"Removed duplicates from {item_id}.")
            dlg.accept()
            
        btn_review.clicked.connect(_review)
        list_widget.itemDoubleClicked.connect(_review)
        d_layout.addWidget(btn_review)
        
        btn_close = QPushButton("Cancel")
        btn_close.clicked.connect(dlg.reject)
        d_layout.addWidget(btn_close)
        
        dlg.exec()
