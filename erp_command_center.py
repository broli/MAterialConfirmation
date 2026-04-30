import customtkinter as ctk
import tkinter.messagebox as messagebox
from tkinter import filedialog
import os
import json
import yaml
import threading
from PIL import Image

from catalog_loader import CatalogLoader
from contract_ingestion import OneClickIngestor
from matching_engine import MatchService
from client_pdf_generator import PDFGenerator
from excel_routing_engine import ExcelRoutingEngine
from database_manager import DatabaseManager
from batch_pdf_ui import BatchPdfIngestWindow

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class ERPCommandCenter(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("PKB ERP Command Center v2.0")
        self.geometry("1100x750")

        self.target_pdf_dir = ""
        self.session_path   = ""
        self.session_data   = {}
        
        # Load database
        self.db_loader = CatalogLoader(base_path="database")
        self.catalog   = self.db_loader.load_all_categories()

        # MatchService — single backend entry point for all DB-lookup logic.
        # debug_mode is wired here so Ollama logs are written when the toggle is on.
        self.match_service = MatchService(
            self.catalog,
            debug_mode=False,
            log_dir="logs",
        )
        self.ingestor = None
        self._busy    = False   # True while background ingestion is running
        
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
        
        self.btn_batch_add = ctk.CTkButton(self.header_frame, text="📄 Batch Add (PDF)", fg_color="green", hover_color="darkgreen", command=self.open_batch_ingest)
        self.btn_batch_add.pack(side="left", padx=10)

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
        
        self.btn_process_unmatched = ctk.CTkButton(self.footer, text="⚙️ Process Unrecognized Items", fg_color="orange", text_color="black", command=self.process_unmatched)
        self.btn_process_unmatched.pack(side="left", padx=10)
        
        self.btn_gen_pdf = ctk.CTkButton(self.footer, text="📄 Generate Client PDF", fg_color="green", command=self.generate_pdf)
        self.btn_gen_pdf.pack(side="right", padx=10)
        
        self.btn_gen_excel = ctk.CTkButton(self.footer, text="📊 Generate Material Cart", fg_color="purple", command=self.generate_excel)
        self.btn_gen_excel.pack(side="right", padx=10)

        # Status Bar
        self.status_bar = ctk.CTkLabel(self, text="Ready.", anchor="w", text_color="gray", font=ctk.CTkFont(size=12))
        self.status_bar.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 5))

        # Startup Ollama check (silent background ping)
        threading.Thread(target=self.check_ollama_background, daemon=True).start()

    # ──────────────────────────────────────────────────────────────────────
    # Busy-state helpers — disable UI while background work runs
    # ──────────────────────────────────────────────────────────────────────

    def check_ollama_background(self):
        """Perform a silent ping on startup to warn user if service is offline."""
        success, _ = self.match_service.check_ollama_ready()
        if not success:
            self.after(0, lambda: self.status_bar.configure(text="⚠️ Ollama Offline (Start Ollama to use AI extraction)", text_color="orange"))
        else:
            self.after(0, lambda: self.status_bar.configure(text="Ready.", text_color="gray"))

    def _set_busy(self, msg: str = "Working...") -> None:
        """Disable interactive buttons and show a status message."""
        self._busy = True
        self.btn_load_dir.configure(state="disabled", text="⏳ Processing...")
        self.status_bar.configure(text=msg, text_color="#1F6AA5")

    def _set_idle(self, msg: str = "Ready.") -> None:
        """Re-enable interactive buttons and clear the busy status."""
        self._busy = False
        self.btn_load_dir.configure(state="normal", text="📁 Pick Job Folder")
        self.status_bar.configure(text=msg, text_color="gray")

    def _update_status(self, msg: str) -> None:
        """Thread-safe status bar update (can be called from any thread)."""
        self.after(0, lambda: self.status_bar.configure(text=msg))

    def toggle_debug(self):
        debug_on = self.debug_var.get()
        # Rebuild MatchService so the LLM client picks up the new debug_mode flag
        self.match_service = MatchService(
            self.catalog,
            debug_mode=debug_on,
            log_dir="logs",
        )
        if self.ingestor:
            self.ingestor.refresh_logger(debug_on)
        label = "ON — writing to logs/" if debug_on else "OFF"
        self._update_status(f"Debug Logging: {label}")

    def load_directory(self):
        if self._busy:
            return
        pdf_path = filedialog.askopenfilename(
            title="Select Contract PDF",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if not pdf_path:
            return

        self.target_pdf_dir = os.path.dirname(pdf_path)
        self.session_path   = os.path.splitext(pdf_path)[0] + ".json"

        if os.path.exists(self.session_path):
            if messagebox.askyesno("Session Found", "A previous session exists for this specific PDF. Resume?"):
                self.load_session(self.session_path)
                return

        # ── Run ingestion in a background thread so the UI stays responsive ──
        self._set_busy("📖 Reading PDF...")
        threading.Thread(
            target=self._ingest_worker,
            args=(pdf_path,),
            daemon=True,
        ).start()

    def _ingest_worker(self, pdf_path: str) -> None:
        """
        Background worker: parse PDF, then run LLM matching.
        All UI updates are dispatched via self.after() for thread safety.
        """
        try:
            # ── Safety Check: Is Ollama up? ──────────────────────────────
            self.after(0, lambda: self.status_bar.configure(text="🔍 Checking AI service..."))
            ready, err = self.match_service.check_ollama_ready()
            if not ready:
                self.after(0, lambda: messagebox.showerror("Ollama Connection Error", 
                    f"AI service is not responding.\n\n{err}\n\nPlease ensure Ollama is running and the model is pulled."))
                self.after(0, lambda: self._set_idle("❌ Ollama Offline."))
                return

            # ── Step 1: Extract data from PDF ──────────────────────────────
            self.after(0, lambda: self.status_bar.configure(text="📖 Extracting PDF..."))
            self.ingestor = OneClickIngestor(pdf_path, self.debug_var.get())
            raw_data = self.ingestor.extract_data()

            if not raw_data.get("line_items"):
                self.after(0, lambda: messagebox.showwarning(
                    "No Items",
                    "Could not extract line items from this PDF.\n"
                    "Make sure the file is a OneClick Contract (not Estimate)."
                ))
                self.after(0, lambda: self._set_idle("⚠️ No items found."))
                return

            # Populate header fields on main thread
            def _fill_header():
                self.entry_client.delete(0, "end")
                self.entry_client.insert(0, raw_data.get("client_name", ""))
                self.entry_po.delete(0, "end")
                self.entry_po.insert(0, raw_data.get("project_po", ""))
            self.after(0, _fill_header)

            n = len(raw_data["line_items"])
            self.after(0, lambda: self.status_bar.configure(
                text=f"📋 PDF done — {n} items extracted. Starting matching..."
            ))

            # ── Step 2: Enrich with LLM + fuzzy matching ───────────────────
            def _status(msg: str):
                self.after(0, lambda: self.status_bar.configure(text=msg))

            self.match_service.enrich_items(
                raw_data["line_items"],
                status_callback=_status,
            )

            # ── Step 3: Commit to session and render ───────────────────────
            self.session_data = raw_data
            self.after(0, self.populate_verification_ui)
            self.after(0, lambda: self._set_idle(f"✅ Loaded {n} items."))

        except Exception as exc:
            self.after(0, lambda: messagebox.showerror("Ingestion Error", str(exc)))
            self.after(0, lambda: self._set_idle(f"❌ Error: {exc}"))

    def open_database_manager(self):
        DatabaseManager(self, self.db_loader)
        
    def open_batch_ingest(self):
        BatchPdfIngestWindow(self, self.db_loader, os.path.join(self.db_loader.base_path, "categories"), os.path.join(self.db_loader.base_path, "assets"), self.populate_verification_ui)
        
    def process_unmatched(self):
        unmatched_items = []
        for item in self.session_data.get("line_items", []):
            match_meta = item.get("_match", {})
            color_code = match_meta.get("color_code", "red")
            is_ignored = match_meta.get("is_ignored", False)
            confirmed = item.get("confirmed", False)
            
            if color_code != "green" and not is_ignored and not confirmed:
                unmatched_items.append(item)
                
        if not unmatched_items:
            messagebox.showinfo("All Good", "No unconfirmed/unrecognized items found in this session.")
            return
            
        BatchPdfIngestWindow(self, self.db_loader, os.path.join(self.db_loader.base_path, "categories"), os.path.join(self.db_loader.base_path, "assets"), self.populate_verification_ui, unmatched_items=unmatched_items)

    def refresh_match_service(self):
        """
        Reinitialise the MatchService after the catalog changes.

        Called by DatabaseManager whenever a product is saved or deleted so
        that the match index stays in sync with the on-disk YAML files.
        """
        self.match_service = MatchService(
            self.catalog,
            debug_mode=self.debug_var.get(),
            log_dir="logs",
        )

    def populate_verification_ui(self):
        """
        Rebuild the two-panel verification UI from the current session data.

        If items already carry ``_match`` data (e.g. after a session resume)
        the enrichment step is skipped.  For fresh data the match is run
        inline (it is fast — LLM was already run in the background worker).
        """
        for w in self.left_panel.winfo_children():  w.destroy()
        for w in self.right_panel.winfo_children(): w.destroy()

        items = self.session_data.get("line_items", [])

        # Only re-enrich if items lack _match metadata (e.g. fresh session start
        # where the background worker hasn't run yet, or a unit-test scenario).
        needs_enrich = any("_match" not in item for item in items)
        if needs_enrich:
            self.match_service.enrich_items(
                items,
                status_callback=lambda msg: self.status_bar.configure(text=msg),
            )

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
        textbox_raw = ctk.CTkTextbox(raw_info_container, wrap="word", fg_color="transparent")
        textbox_raw.insert("0.0", raw_txt)
        textbox_raw.configure(state="disabled")
        textbox_raw.pack(padx=10, pady=10, fill="both", expand=True)
        
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
        if not self.session_path:
            return
        # Save current client/po edits
        self.session_data["client_name"] = self.entry_client.get().strip()
        self.session_data["project_po"] = self.entry_po.get().strip()
        
        try:
            with open(self.session_path, "w") as f:
                json.dump(self.session_data, f, indent=4)
            self.status_bar.configure(text=f"💾 Session saved: {os.path.basename(self.session_path)}")
            if not silent:
                messagebox.showinfo("Saved", f"Session saved to:\n{self.session_path}")
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
