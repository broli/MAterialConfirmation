import customtkinter as ctk
import tkinter.messagebox as messagebox
from tkinter import filedialog
import os
import json
import yaml
from PIL import Image

from catalog_loader import CatalogLoader
from contract_ingestion import OneClickIngestor
from matching_engine import MatchService
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
        
        # MatchService is the single backend entry point for all DB-lookup logic.
        # The UI never calls MatchingEngine directly.
        self.match_service = MatchService(self.catalog)
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

        self.hide_ignored_var = ctk.BooleanVar(value=True)
        self.switch_hide_ignored = ctk.CTkSwitch(info_frame, text="Hide Ignored Items", variable=self.hide_ignored_var, command=self.populate_verification_ui)
        self.switch_hide_ignored.pack(side="right", padx=10)
        
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

    def refresh_match_service(self):
        """
        Reinitialise the MatchService after the catalog changes.

        Called by DatabaseManager whenever a product is saved or deleted so
        that the match index stays in sync with the on-disk YAML files.
        The UI does not need to know how the service is built — it just
        triggers this method and the backend handles the rest.
        """
        self.match_service = MatchService(self.catalog)

    def populate_verification_ui(self):
        """
        Rebuild the two-panel verification UI from the current session data.

        This method is *display-only*: it asks MatchService for match metadata
        and renders it.  No matching logic lives here.
        """
        # Clear existing widgets from both panels.
        for w in self.left_panel.winfo_children(): w.destroy()
        for w in self.right_panel.winfo_children(): w.destroy()

        items = self.session_data.get("line_items", [])

        # Enrich every item with match metadata in one batch call.
        # This attaches a '_match' dict to each item (in-place) without touching
        # the session fields that are persisted to disk.
        self.match_service.enrich_items(items)

        for i, item in enumerate(items):
            desc  = item.get("raw_description", "")
            qty   = item.get("qty", 1)
            room  = item.get("room", "Misc")

            # Unpack pre-resolved match metadata from the service.
            meta       = item["_match"]
            match_id   = meta["match_id"]
            conf       = meta["confidence"]
            color_hex  = meta["color_hex"]
            is_ignored = meta["is_ignored"]
            confirmed  = item.get("confirmed", False)

            # Skip rendering if this item is marked to be ignored and the user has toggled the hide switch
            if is_ignored and self.hide_ignored_var.get():
                continue

            # --- Left Panel: Extracted Line Item Row ---
            row_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)

            # Full-width clickable button used as a hover-able row background.
            btn_row = ctk.CTkButton(
                row_frame,
                text="",
                fg_color="transparent",
                hover_color=("gray70", "gray30"),
                height=35,
                anchor="w",
                command=lambda val=item: self.inspect_item(val)
            )
            btn_row.pack(fill="x", padx=5)

            # Fixed-position prefix label (item number, room, qty).
            prefix_txt = f"{i+1}. [{room}] Qty: {qty}"
            lbl_prefix = ctk.CTkLabel(btn_row, text=prefix_txt, font=ctk.CTkFont(weight="bold"), anchor="w")
            lbl_prefix.place(relx=0, rely=0.5, anchor="w", x=10)

            # Scrolling description label — will be clipped by the button boundary.
            lbl_desc = ctk.CTkLabel(btn_row, text=f"| {desc}", anchor="w")
            lbl_desc.place(relx=0, rely=0.5, anchor="w", x=160)

            # Propagate click events from child labels to the parent command.
            lbl_prefix.bind("<Button-1>", lambda e, v=item: self.inspect_item(v))
            lbl_desc.bind("<Button-1>",   lambda e, v=item: self.inspect_item(v))

            # --- Right Panel: Match Result ---
            right_f = ctk.CTkFrame(self.right_panel)
            right_f.pack(fill="x", pady=5)

            # Traffic-light confidence indicator — colour resolved entirely by the service.
            indicator = ctk.CTkLabel(right_f, text="●", text_color=color_hex, font=ctk.CTkFont(size=20))
            indicator.pack(side="left", padx=5)

            # Human-readable status string.
            if confirmed:
                info_str = f"{i+1}. IGNORED: {match_id}" if is_ignored else f"{i+1}. CONFIRMED: {match_id}"
            else:
                info_str = f"{i+1}. Match: {match_id} ({conf:.1f}%)" if match_id else f"{i+1}. No Match Found"

            ctk.CTkLabel(right_f, text=info_str, width=250, anchor="w").pack(side="left", padx=5)

            # Confirm button — disabled once the user has already confirmed the item.
            if confirmed:
                btn_color = "gray50" if is_ignored else "green"
                btn_text  = "Ignored" if is_ignored else "Confirmed"
                btn_state = "disabled"
            else:
                btn_color = "#153E83"
                btn_text  = "Confirm"
                btn_state = "normal"

            btn_verify = ctk.CTkButton(
                right_f, text=btn_text, width=80, fg_color=btn_color, state=btn_state,
                command=lambda idx=i, mid=match_id: self.confirm_item(idx, mid)
            )
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
        top.geometry("900x650")
        top.transient(self)
        top.grab_set()
        top.focus_set()
        top.attributes("-topmost", True)
        
        # Grid layout for top level
        top.grid_columnconfigure(0, weight=1)
        top.grid_columnconfigure(1, weight=2)
        top.grid_rowconfigure(0, weight=1)
        
        # Left side: PDF Extracted Raw
        raw_f = ctk.CTkFrame(top)
        raw_f.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        ctk.CTkLabel(raw_f, text="Extracted from Contract", font=ctk.CTkFont(weight="bold", size=16)).pack(pady=10)
        
        raw_info_container = ctk.CTkScrollableFrame(raw_f, fg_color="transparent")
        raw_info_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        raw_txt = f"Room: {item.get('room')}\nQty: {item.get('qty')}\n\nDescription:\n{item.get('raw_description')}"
        lbl_raw = ctk.CTkLabel(raw_info_container, text=raw_txt, justify="left", wraplength=450, anchor="nw")
        lbl_raw.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Right side: DB Knowledge center
        db_panel = ctk.CTkFrame(top)
        db_panel.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        db_panel.grid_columnconfigure(0, weight=1)
        db_panel.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(db_panel, text="Database Entry Details", font=ctk.CTkFont(weight="bold", size=16)).grid(row=0, column=0, pady=10)
        
        # Scrollable area for all fields
        scroll_f = ctk.CTkScrollableFrame(db_panel)
        scroll_f.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # Delegate match resolution to the service.
        # resolve_match() honours confirmed items and runs the fuzzy engine
        # for unconfirmed ones — the UI does not need to know which path is taken.
        meta     = self.match_service.resolve_match(item)
        match_id = meta["match_id"]
            
        if match_id and match_id in self.catalog:
            db_item = self.catalog[match_id]
            
            # 1. Product Image Display
            image_file = db_item.get("printable", {}).get("image_file")
            if image_file:
                img_path = os.path.join(self.db_loader.assets_path, image_file)
                if os.path.exists(img_path):
                    try:
                        pil_img = Image.open(img_path)
                        # Maintain aspect ratio for preview
                        w, h = pil_img.size
                        max_size = 300
                        if w > h:
                            new_w = max_size
                            new_h = int(h * (max_size / w))
                        else:
                            new_h = max_size
                            new_w = int(w * (max_size / h))
                        
                        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(new_w, new_h))
                        img_lbl = ctk.CTkLabel(scroll_f, image=ctk_img, text="")
                        img_lbl.pack(pady=15)
                    except Exception as e:
                        ctk.CTkLabel(scroll_f, text=f"Error loading image: {e}", text_color="red").pack()
                else:
                    ctk.CTkLabel(scroll_f, text=f"Image not found: {image_file}", text_color="orange").pack(pady=5)
            
            # Formatting helpers
            def add_header(txt):
                header_f = ctk.CTkFrame(scroll_f, fg_color="transparent")
                header_f.pack(fill="x", pady=(20, 5))
                ctk.CTkLabel(header_f, text=txt, font=ctk.CTkFont(weight="bold", size=14), text_color="#1F6AA5").pack(side="left")
                ctk.CTkFrame(scroll_f, height=2, fg_color=("gray80", "gray30")).pack(fill="x", pady=(0, 10))

            def add_field(key, val):
                f = ctk.CTkFrame(scroll_f, fg_color="transparent")
                f.pack(fill="x", pady=2)
                ctk.CTkLabel(f, text=f"{key}:", font=ctk.CTkFont(weight="bold"), width=130, anchor="w").pack(side="left", padx=(5, 0))
                
                if isinstance(val, dict):
                    val_str = ", ".join([f"{k}: {v}" for k, v in val.items()])
                else:
                    val_str = str(val) if val is not None else "N/A"
                    
                ctk.CTkLabel(f, text=val_str, wraplength=400, justify="left", anchor="w").pack(side="left", fill="x", expand=True, padx=5)

            # 2. Core ERP Section
            add_header("CORE ERP / PURCHASING INFO")
            core_fields = ['id', 'sku', 'brand', 'provider', 'routing_tag', 'purchase_link', 'category_file', 'verified_oneclick']
            for field in core_fields:
                if field in db_item:
                    add_field(field.replace('_', ' ').title(), db_item[field])
            
            # Show any extra fields at top level
            for k, v in db_item.items():
                if k not in core_fields and k not in ['printable', 'oneclick_description']:
                    add_field(k.replace('_', ' ').title(), v)
            
            # Match String (Tech details)
            add_header("MATCHING ENGINE METADATA")
            target_desc = db_item.get("oneclick_description", "N/A")
            if target_desc and len(target_desc) > 100:
                target_desc = target_desc[:97] + "..."
            add_field("Target String", target_desc)

            # 3. Printable Section
            add_header("PRINTABLE / CLIENT-FACING INFO")
            printable = db_item.get("printable", {})
            if printable:
                for k, v in printable.items():
                    if k != 'image_file': 
                        add_field(k.replace('_', ' ').title(), v)
            else:
                ctk.CTkLabel(scroll_f, text="Item is hidden from PDF (No printable block).", text_color="gray").pack(anchor="w", padx=20)
                
        else:
            ctk.CTkLabel(scroll_f, text="No properties matched in database.", text_color="red", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=100)

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
                    # Database-driven classification: skip items flagged as IGNORE
                    if db_item.get("routing_tag", "").strip().upper() == "IGNORE":
                        continue
                        
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
