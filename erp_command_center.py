import customtkinter as ctk
import tkinter.messagebox as messagebox
from tkinter import filedialog
import os
import json
import yaml

from catalog_loader import CatalogLoader
from contract_ingestion import OneClickIngestor
from matching_engine import MatchingEngine
from client_pdf_generator import PDFGenerator
from excel_routing_engine import ExcelRoutingEngine

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class ERPCommandCenter(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("PKB ERP Command Center v2.0")
        self.geometry("1100x750")

        self.target_pdf_dir = ""
        self.session_data = {}
        
        # Load database
        self.db_loader = CatalogLoader(base_path="database")
        self.catalog = self.db_loader.load_all_categories()
        
        self.matcher = MatchingEngine(self.catalog)
        self.ingestor = None
        
        # UI layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        
        ctk.CTkLabel(self.header_frame, text="Command Center", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        
        self.debug_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(self.header_frame, text="Debug Mode (Log Parsing)", variable=self.debug_var, command=self.toggle_debug).pack(side="right", padx=10)

        self.btn_load_dir = ctk.CTkButton(self.header_frame, text="📁 Pick Job Folder", command=self.load_directory)
        self.btn_load_dir.pack(side="right", padx=10)

        # Main Workspace - Split Screen
        self.workspace = ctk.CTkFrame(self)
        self.workspace.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.workspace.grid_columnconfigure(0, weight=1)
        self.workspace.grid_columnconfigure(1, weight=1)
        self.workspace.grid_rowconfigure(2, weight=1)
        
        # Top Info (Client/PO)
        info_frame = ctk.CTkFrame(self.workspace, fg_color="transparent")
        info_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        ctk.CTkLabel(info_frame, text="Client Name:").pack(side="left", padx=5)
        self.entry_client = ctk.CTkEntry(info_frame, width=200)
        self.entry_client.pack(side="left", padx=5)
        
        ctk.CTkLabel(info_frame, text="Project PO:").pack(side="left", padx=(20, 5))
        self.entry_po = ctk.CTkEntry(info_frame, width=150)
        self.entry_po.pack(side="left", padx=5)
        
        # Left Panel - Extracted Data
        self.left_panel = ctk.CTkScrollableFrame(self.workspace, label_text="Extracted Contract Lines")
        self.left_panel.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)

        # Right Panel - Database Match & Verify
        self.right_panel = ctk.CTkScrollableFrame(self.workspace, label_text="Suggested DB Match (Action Required)")
        self.right_panel.grid(row=2, column=1, sticky="nsew", padx=10, pady=10)

        # Footer Actions
        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        
        self.btn_save_session = ctk.CTkButton(self.footer, text="💾 Save Session", fg_color="gray", command=self.save_session)
        self.btn_save_session.pack(side="left", padx=10)
        
        self.btn_gen_pdf = ctk.CTkButton(self.footer, text="📄 Generate Client PDF", fg_color="green", command=self.generate_pdf)
        self.btn_gen_pdf.pack(side="right", padx=10)
        
        self.btn_gen_excel = ctk.CTkButton(self.footer, text="📊 Generate Material Cart", fg_color="purple", command=self.generate_excel)
        self.btn_gen_excel.pack(side="right", padx=10)

    def toggle_debug(self):
        if self.ingestor:
            self.ingestor.debug_mode = self.debug_var.get()
            self.ingestor.logger.setLevel(10 if self.debug_var.get() else 20)

    def load_directory(self):
        dir_path = filedialog.askdirectory(title="Select Folder containing PDF contract & estimate")
        if not dir_path:
            return
            
        self.target_pdf_dir = dir_path
        session_file = os.path.join(dir_path, "session_data.json")
        
        if os.path.exists(session_file):
            if messagebox.askyesno("Session Found", "A previous session exists in this folder. Do you want to resume?"):
                self.load_session(session_file)
                return
        
        # New Ingestion
        self.ingestor = OneClickIngestor(dir_path, self.debug_var.get())
        raw_data = self.ingestor.extract_data()
        
        if not raw_data.get("line_items"):
            messagebox.showwarning("No Items", "Could not extract line items. Ensure Estimate/Contract PDFs exist.")
        
        self.entry_client.delete(0, "end")
        self.entry_client.insert(0, raw_data.get("client_name", ""))
        
        self.entry_po.delete(0, "end")
        self.entry_po.insert(0, raw_data.get("project_po", ""))
        
        self.session_data = raw_data
        self.populate_verification_ui()

    def populate_verification_ui(self):
        # Clear existing
        for w in self.left_panel.winfo_children(): w.destroy()
        for w in self.right_panel.winfo_children(): w.destroy()
        
        items = self.session_data.get("line_items", [])
        
        for i, item in enumerate(items):
            desc = item.get("raw_description", "")
            qty = item.get("qty", 1)
            
            # Left Panel
            left_f = ctk.CTkFrame(self.left_panel)
            left_f.pack(fill="x", pady=5)
            ctk.CTkLabel(left_f, text=f"Qty: {qty} | {desc}", wraplength=400, justify="left").pack(anchor="w", padx=5, pady=5)
            
            # Right Panel Matching
            right_f = ctk.CTkFrame(self.right_panel)
            right_f.pack(fill="x", pady=5)
            
            # Use match engine
            match_id, match_str, conf = self.matcher.match_item(desc)
            color = self.matcher.get_color_code(conf)
            
            # Visual indicator (Traffic light)
            color_hex = {"green": "#00FF00", "yellow": "#FFFF00", "red": "#FF0000"}
            indicator = ctk.CTkLabel(right_f, text="●", text_color=color_hex.get(color, "gray"), font=ctk.CTkFont(size=20))
            indicator.pack(side="left", padx=5)
            
            info_str = f"Match: {match_id} ({conf:.1f}%)" if match_id else "No Match Found"
            ctk.CTkLabel(right_f, text=info_str, width=250, anchor="w").pack(side="left", padx=5)
            
            btn_verify = ctk.CTkButton(right_f, text="Confirm", width=80, fg_color="#153E83", command=lambda idx=i: self.confirm_item(idx))
            btn_verify.pack(side="right", padx=5)
            
            # Here we would add an Edit dropdown. For now just placeholder
            btn_edit = ctk.CTkButton(right_f, text="Edit", width=60, fg_color="gray")
            btn_edit.pack(side="right", padx=5)

    def confirm_item(self, idx):
        # Placeholder for confirming item matched
        pass

    def save_session(self):
        if not self.target_pdf_dir:
            return
        # Save current client/po edits
        self.session_data["client_name"] = self.entry_client.get().strip()
        self.session_data["project_po"] = self.entry_po.get().strip()
        
        path = os.path.join(self.target_pdf_dir, "session_data.json")
        with open(path, "w") as f:
            json.dump(self.session_data, f, indent=4)
        messagebox.showinfo("Saved", f"Session saved to:\n{path}")

    def load_session(self, path):
        with open(path, "r") as f:
            self.session_data = json.load(f)
        
        self.entry_client.delete(0, "end")
        self.entry_client.insert(0, self.session_data.get("client_name", ""))
        self.entry_po.delete(0, "end")
        self.entry_po.insert(0, self.session_data.get("project_po", ""))
        
        self.populate_verification_ui()

    def _prepare_payload(self):
        # Build the final payload representing all mapped items from the catalog
        self.save_session()
        payload = {
            "client_info": {
                "name": self.session_data.get("client_name", ""),
                "project": "PO " + self.session_data.get("project_po", "")
            },
            "products": []
        }
        
        for item in self.session_data.get("line_items", []):
            if "matched_id" in item and item["matched_id"]:
                db_item = self.catalog.get(item["matched_id"], {}).copy()
                if db_item:
                    db_item["qty"] = item.get("qty", 1)
                    payload["products"].append(db_item)
        return payload

    def generate_pdf(self):
        payload = self._prepare_payload()
        if not payload["products"]:
            messagebox.showwarning("Warning", "No confirmed products to generate PDF.")
            return
            
        generator = PDFGenerator()
        out_file = generator.create_pdf(payload)
        messagebox.showinfo("Success", f"Client PDF Generated!\n{out_file}")

    def generate_excel(self):
        payload = self._prepare_payload()
        if not payload["products"]:
            messagebox.showwarning("Warning", "No confirmed products to generate Excel.")
            return
            
        # We emulate the verified_session_data structure expected by excel_routing_engine
        excel_payload = {
            "client_name": payload["client_info"]["name"],
            "project_po": self.session_data.get("project_po", ""),
            "products": payload["products"]
        }
        generator = ExcelRoutingEngine()
        out_file = generator.generate_excel(excel_payload)
        if out_file:
            messagebox.showinfo("Success", f"Material Cart Excel Generated!\n{out_file}")
        else:
            messagebox.showerror("Error", "Missing Excel Template file in /raw dir.")
