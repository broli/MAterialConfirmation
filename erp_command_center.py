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
from database_manager import DatabaseManager

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
        self.btn_load_dir.pack(side="left", padx=20)

        self.btn_manage_db = ctk.CTkButton(self.header_frame, text="⚙️ Manage Database", fg_color="#153E83", hover_color="#0d2b61", command=self.open_database_manager)
        self.btn_manage_db.pack(side="right", padx=10)

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
        
        self.btn_save_session = ctk.CTkButton(self.footer, text="💾 Save Session", command=lambda: self.save_session(silent=False))
        self.btn_save_session.pack(side="left", padx=10)
        
        self.btn_gen_pdf = ctk.CTkButton(self.footer, text="📄 Generate Client PDF", fg_color="green", command=self.generate_pdf)
        self.btn_gen_pdf.pack(side="right", padx=10)
        
        self.btn_gen_excel = ctk.CTkButton(self.footer, text="📊 Generate Material Cart", fg_color="purple", command=self.generate_excel)
        self.btn_gen_excel.pack(side="right", padx=10)

        # Status Bar
        self.status_bar = ctk.CTkLabel(self, text="Ready.", anchor="w", text_color="gray", font=ctk.CTkFont(size=12))
        self.status_bar.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 5))

    def toggle_debug(self):
        if self.ingestor:
            self.ingestor.refresh_logger(self.debug_var.get())
            self.status_bar.configure(text=f"Debug Logging: {'ON (Job Folder)' if self.debug_var.get() else 'OFF (Global)'}")

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

    def open_database_manager(self):
        DatabaseManager(self, self.db_loader)

    def populate_verification_ui(self):
        # Clear existing
        for w in self.left_panel.winfo_children(): w.destroy()
        for w in self.right_panel.winfo_children(): w.destroy()
        
        items = self.session_data.get("line_items", [])
        
        for i, item in enumerate(items):
            desc = item.get("raw_description", "")
            qty = item.get("qty", 1)
            room = item.get("room", "Misc")
            confirmed = item.get("confirmed", False)
            
            # Left Panel
            left_f = ctk.CTkFrame(self.left_panel)
            left_f.pack(fill="x", pady=5)
            
            lbl_text = f"[{room}] Qty: {qty} | {desc}"
            # Make the left label a clickable flat button
            btn_inspect = ctk.CTkButton(left_f, text=lbl_text, anchor="w", fg_color="transparent", text_color=("black","white"), hover_color=("gray70","gray30"), command=lambda val=item: self.inspect_item(val))
            btn_inspect.pack(fill="x", padx=5, pady=5)
            
            # Right Panel Matching
            right_f = ctk.CTkFrame(self.right_panel)
            right_f.pack(fill="x", pady=5)
            
            # If already confirmed, use the saved matched_id, else query engine
            if confirmed and "matched_id" in item:
                match_id = item["matched_id"]
                conf = 100.0
            else:
                match_id, match_str, conf = self.matcher.match_item(desc)
                
            color = self.matcher.get_color_code(conf) if not confirmed else "green"
            
            # Visual indicator (Traffic light)
            color_hex = {"green": "#00FF00", "yellow": "#FFFF00", "red": "#FF0000"}
            indicator = ctk.CTkLabel(right_f, text="●", text_color=color_hex.get(color, "gray"), font=ctk.CTkFont(size=20))
            indicator.pack(side="left", padx=5)
            
            info_str = f"Match: {match_id} ({conf:.1f}%)" if match_id else "No Match Found"
            if confirmed:
                info_str = f"CONFIRMED: {match_id}"
                
            ctk.CTkLabel(right_f, text=info_str, width=250, anchor="w").pack(side="left", padx=5)
            
            btn_color = "green" if confirmed else "#153E83"
            btn_text = "Confirmed" if confirmed else "Confirm"
            btn_state = "disabled" if confirmed else "normal"
            
            btn_verify = ctk.CTkButton(right_f, text=btn_text, width=80, fg_color=btn_color, state=btn_state, command=lambda idx=i, mid=match_id: self.confirm_item(idx, mid))
            btn_verify.pack(side="right", padx=5)

    def confirm_item(self, idx, match_id):
        if not match_id:
            messagebox.showwarning("No Match", "Cannot confirm an item with no matched ID.")
            return
            
        self.session_data["line_items"][idx]["matched_id"] = match_id
        self.session_data["line_items"][idx]["confirmed"] = True
        self.save_session(silent=True)
        self.status_bar.configure(text=f"✅ Assigned: {match_id}")
        self.populate_verification_ui()

    def inspect_item(self, item):
        top = ctk.CTkToplevel(self)
        top.title("Inspect Item Match")
        top.geometry("600x400")
        top.attributes("-topmost", True)
        
        # Left side: PDF Extracted Raw
        raw_f = ctk.CTkFrame(top)
        raw_f.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(raw_f, text="Extracted from Contract", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        raw_txt = f"Room: {item.get('room')}\nQty: {item.get('qty')}\n\nDescription:\n{item.get('raw_description')}"
        lbl_raw = ctk.CTkLabel(raw_f, text=raw_txt, justify="left", wraplength=250)
        lbl_raw.pack(padx=10, pady=10, anchor="nw")
        
        # Right side: DB Knowledge
        db_f = ctk.CTkFrame(top)
        db_f.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(db_f, text="Database Properties", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        match_id = item.get("matched_id", None)
        if not match_id:
            # Predict it live
            match_id, _, _ = self.matcher.match_item(item.get("raw_description", ""))
            
        if match_id and match_id in self.catalog:
            db_item = self.catalog[match_id]
            db_txt = f"ID: {db_item.get('id')}\nBrand: {db_item.get('brand')}\nModel: {db_item.get('model')}\nType: {db_item.get('type')}\nFinish: {db_item.get('finish')}\nRouting: {db_item.get('routing_tag', 'Standard')}"
            lbl_db = ctk.CTkLabel(db_f, text=db_txt, justify="left", wraplength=250)
            lbl_db.pack(padx=10, pady=10, anchor="nw")
        else:
            ctk.CTkLabel(db_f, text="No properties matched in database.", text_color="red").pack(pady=10)

    def save_session(self, silent=True):
        if not self.target_pdf_dir:
            return
        # Save current client/po edits
        self.session_data["client_name"] = self.entry_client.get().strip()
        self.session_data["project_po"] = self.entry_po.get().strip()
        
        path = os.path.join(self.target_pdf_dir, "session_data.json")
        try:
            with open(path, "w") as f:
                json.dump(self.session_data, f, indent=4)
            self.status_bar.configure(text="💾 Session autosaved correctly.")
            if not silent:
                messagebox.showinfo("Saved", f"Session saved to:\n{path}")
        except Exception as e:
            self.status_bar.configure(text=f"Error saving session: {e}", text_color="red")

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
            if item.get("confirmed") and item.get("matched_id"):
                db_item = self.catalog.get(item["matched_id"], {}).copy()
                if db_item:
                    db_item["qty"] = item.get("qty", 1)
                    db_item["room"] = item.get("room", "General")
                    payload["products"].append(db_item)
        return payload

    def generate_pdf(self):
        payload = self._prepare_payload()
        if not payload["products"]:
            messagebox.showwarning("Warning", "No confirmed products to generate PDF.")
            return
            
        # Target the specific job folder selected by the user
        output_dir = os.path.join(self.target_pdf_dir, "ERP_Automated_Output")
        os.makedirs(output_dir, exist_ok=True)
            
        generator = PDFGenerator(output_path=output_dir)
        out_file = generator.create_pdf(payload)
        messagebox.showinfo("Success", f"Client PDF Generated!\n{out_file}")
        self.status_bar.configure(text=f"✅ PDF saved to: {os.path.basename(out_file)}")

    def generate_excel(self):
        payload = self._prepare_payload()
        if not payload["products"]:
            messagebox.showwarning("Warning", "No confirmed products to generate Excel.")
            return

        # Target the specific job folder selected by the user
        output_dir = os.path.join(self.target_pdf_dir, "ERP_Automated_Output")
        os.makedirs(output_dir, exist_ok=True)
            
        # We emulate the verified_session_data structure expected by excel_routing_engine
        excel_payload = {
            "client_name": payload["client_info"]["name"],
            "project_po": self.session_data.get("project_po", ""),
            "products": payload["products"]
        }
        generator = ExcelRoutingEngine(output_dir=output_dir)
        out_file = generator.generate_excel(excel_payload)
        if out_file:
            messagebox.showinfo("Success", f"Material Cart Excel Generated!\n{out_file}")
            self.status_bar.configure(text=f"✅ Excel saved to: {os.path.basename(out_file)}")
        else:
            messagebox.showerror("Error", "Missing Excel Template file in /database/templates dir.")
