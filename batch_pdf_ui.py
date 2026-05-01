import customtkinter as ctk
import tkinter.messagebox as messagebox
from tkinter import filedialog
import os
import yaml
import shutil
import threading
from PIL import Image

from schema.contract_item import ContractItem
from config_manager import ConfigManager
from contract_ingestion import OneClickIngestor
from product_service import ProductService
import matching_engine
from llm_service import LocalLLMClient

class BatchPdfIngestWindow(ctk.CTkToplevel):
    def __init__(self, master, db_loader, categories_path, assets_path, refresh_callback, unmatched_items=None):
        super().__init__(master)
        
        self.title("Batch Add Unmatched PDF Items")
        self.geometry("1100x700")
        self.transient(master)
        self.grab_set()
        self.focus_set()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))
        
        self.db_loader = db_loader
        self.categories_path = categories_path
        self.assets_path = assets_path
        self.refresh_callback = refresh_callback
        
        self.llm_client = LocalLLMClient(log_callback=self.log_to_console)
        self.selected_raw_text = ""
        self.image_path_var = ctk.StringVar(value="")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)
        
        self.build_left_pane(bool(unmatched_items))
        self.build_right_pane()
        
        if unmatched_items:
            self.unmatched_items = []
            for it in unmatched_items:
                if it["raw_description"] not in [x["raw_description"] for x in self.unmatched_items]:
                    self.unmatched_items.append(it)
            self.after(100, self._render_queue)
        
    def build_left_pane(self, has_items=False):
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.left_frame.grid_rowconfigure(2, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.left_frame, text="1. Select Job Folder", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, pady=(10, 5), padx=10, sticky="w")
        btn_browse = ctk.CTkButton(self.left_frame, text="Browse for Agreement...", command=self.load_pdf)
        btn_browse.grid(row=1, column=0, pady=5, padx=10, sticky="ew")
        
        if has_items:
            btn_browse.configure(state="disabled", text="Items loaded from session.")
        
        self.queue_frame = ctk.CTkScrollableFrame(self.left_frame)
        self.queue_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        
    def build_right_pane(self):
        self.right_container = ctk.CTkFrame(self, fg_color="transparent")
        self.right_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.right_container.grid_columnconfigure(0, weight=1)
        self.right_container.grid_rowconfigure(0, weight=1)

        self.right_frame = ctk.CTkScrollableFrame(self.right_container)
        self.right_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self.right_frame.grid_columnconfigure(1, weight=1)
        
        header_frame_2 = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        header_frame_2.grid(row=0, column=0, columnspan=2, pady=(10, 20), sticky="ew")
        
        ctk.CTkLabel(header_frame_2, text="2. Modify extracted details", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        ctk.CTkButton(header_frame_2, text="or pick one from the database", width=180, fg_color="gray20", hover_color="gray30", command=self.open_database_picker).pack(side="right", padx=10)
        
        # Identity
        ctk.CTkLabel(self.right_frame, text="Category File *").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.cat_entry = ctk.CTkComboBox(self.right_frame, values=self._get_existing_categories(), command=self.on_category_change)
        self.cat_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        if self._get_existing_categories():
            self.cat_entry.set(self._get_existing_categories()[0])
            
        ctk.CTkLabel(self.right_frame, text="Unique ID *").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.id_entry = ctk.CTkEntry(self.right_frame)
        self.id_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        ctk.CTkLabel(self.right_frame, text="Brand").grid(row=3, column=0, padx=10, pady=5, sticky="e")
        self.brand_entry = ctk.CTkEntry(self.right_frame)
        self.brand_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        
        ctk.CTkLabel(self.right_frame, text="OneClick Description *").grid(row=4, column=0, padx=10, pady=5, sticky="e")
        self.oneclick_entry = ctk.CTkEntry(self.right_frame)
        self.oneclick_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        
        ctk.CTkLabel(self.right_frame, text="Routing Tag *").grid(row=5, column=0, padx=10, pady=5, sticky="e")
        self.routing_entry = ctk.CTkComboBox(self.right_frame, values=["IGNORE", "WAREHOUSE", "PROCURE", "WH_OR_PROCURE"])
        self.routing_entry.grid(row=5, column=1, padx=10, pady=5, sticky="ew")
        self.routing_entry.set("WAREHOUSE")
        
        # Printable attributes
        ctk.CTkLabel(self.right_frame, text="Finish (Color)").grid(row=6, column=0, padx=10, pady=5, sticky="e")
        self.finish_entry = ctk.CTkEntry(self.right_frame)
        self.finish_entry.grid(row=6, column=1, padx=10, pady=5, sticky="ew")
        
        ctk.CTkLabel(self.right_frame, text="Marketing Description").grid(row=7, column=0, padx=10, pady=5, sticky="e")
        self.desc_entry = ctk.CTkEntry(self.right_frame)
        self.desc_entry.grid(row=7, column=1, padx=10, pady=5, sticky="ew")
        
        # Image selection
        img_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        img_frame.grid(row=8, column=0, columnspan=2, pady=10, sticky="ew", padx=10)
        ctk.CTkButton(img_frame, text="Select Image...", command=self.browse_image).pack(side="left", padx=10)
        ctk.CTkLabel(img_frame, textvariable=self.image_path_var).pack(side="left")
        
        # Dynamic Dimensions
        self.dimension_rows = []
        
        dim_header_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        dim_header_frame.grid(row=9, column=0, columnspan=2, padx=10, pady=(5,0), sticky="ew")
        ctk.CTkLabel(dim_header_frame, text="Dimensions", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        ctk.CTkButton(dim_header_frame, text="+ Add Measurement", width=120, command=self.add_dimension_row).pack(side="right", padx=5)
        
        self.dimensions_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.dimensions_frame.grid(row=10, column=0, columnspan=2, padx=10, pady=(0,5), sticky="ew")
        
        # Action
        self.btn_compile = ctk.CTkButton(self.right_frame, text="Save", fg_color="green", command=self.initiate_save)
        self.btn_compile.grid(row=11, column=0, columnspan=2, pady=30)
        
        # Info label
        self.status_lbl = ctk.CTkLabel(self.right_frame, text="", text_color="yellow")
        self.status_lbl.grid(row=12, column=0, columnspan=2)

        # Terminal output stick to bottom
        self.console_container = ctk.CTkFrame(self.right_container, fg_color="transparent")
        self.console_container.grid(row=1, column=0, sticky="nsew")
        self.console_container.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(self.console_container, mode="indeterminate")
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.progress_bar.set(0)

        header_frame_log = ctk.CTkFrame(self.console_container, fg_color="transparent")
        header_frame_log.grid(row=1, column=0, pady=(0, 2), sticky="ew")
        
        ctk.CTkLabel(header_frame_log, text="Terminal Log", font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkButton(header_frame_log, text="Check AI Connection", width=140, height=20, font=ctk.CTkFont(size=10), command=self.check_ai_connectivity).pack(side="right", padx=5)
        
        self.console_box = ctk.CTkTextbox(self.console_container, height=150, fg_color="black", text_color="#00FF00", font=ctk.CTkFont(family="Courier", size=11))
        self.console_box.grid(row=2, column=0, sticky="ew")
        self.console_box.configure(state="disabled")

    def add_dimension_row(self, key="", value=""):
        """Add one dimension input row. Delegates to ProductService helper."""
        ProductService.build_dimension_rows(
            self.dimensions_frame,
            existing_dims={key.title(): value} if key else {},
            row_store=self.dimension_rows,
        )

    def open_database_picker(self):
        DatabasePicker(self, self.master.catalog, self.populate_from_existing_item)

    def populate_from_existing_item(self, item):
        # Clear fields
        self.id_entry.delete(0, 'end')
        self.brand_entry.delete(0, 'end')
        self.oneclick_entry.delete(0, 'end')
        self.finish_entry.delete(0, 'end')
        self.desc_entry.delete(0, 'end')
        for w in self.dimensions_frame.winfo_children():
            w.destroy()
        self.dimension_rows = []
        self.image_path_var.set("")
        
        # Fill fields
        self.id_entry.insert(0, item.get("id", ""))
        self.brand_entry.insert(0, item.get("brand", ""))
        self.oneclick_entry.insert(0, item.get("oneclick_description", ""))
        
        cat_file = item.get("category_file", "")
        if cat_file:
            if not cat_file.endswith(".yaml"): cat_file += ".yaml"
            self.cat_entry.set(cat_file)
            
        self.routing_entry.set(item.get("routing_tag", "WAREHOUSE"))
        
        printable = item.get("printable", {})
        if printable:
            self.finish_entry.insert(0, printable.get("finish", ""))
            self.desc_entry.insert(0, printable.get("description", ""))
            
            dims = printable.get("dimensions", {})
            for k, v in dims.items():
                self.add_dimension_row(k, v)
                
            if printable.get("image_file"):
                # Just show the filename for now
                self.image_path_var.set(printable.get("image_file"))

    def on_category_change(self, choice):
        if choice == "ignore.yaml":
            if not self.id_entry.get().strip():
                # We need a db loader instance. The master catalog is passed or we can instantiate one
                from catalog_loader import CatalogLoader
                loader = CatalogLoader()
                next_id = loader.get_next_ignore_id()
                self.id_entry.insert(0, next_id)

    def browse_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.jpeg *.png")])
        if file_path:
            self.image_path_var.set(file_path)

    def log_to_console(self, msg):
        def _update():
            if self.winfo_exists() and self.console_box.winfo_exists():
                self.console_box.configure(state="normal")
                self.console_box.insert("end", msg + "\n")
                self.console_box.see("end")
                self.console_box.configure(state="disabled")
        self.after(0, _update)

    def check_ai_connectivity(self):
        self.log_to_console("--- Testing Ollama Connection ---")
        def _task():
            success, msg = self.llm_client.check_connection()
            color = "SUCCESS" if success else "FAILURE"
            self.log_to_console(f"Result: {color} - {msg}")
            if success:
                self.log_to_console(f"Model: {self.llm_client.model} is ready.")
            self.log_to_console("---------------------------------")
            
        threading.Thread(target=_task, daemon=True).start()

    def _get_existing_categories(self):
        if not os.path.exists(self.categories_path): return []
        return [f for f in os.listdir(self.categories_path) if f.endswith('.yaml')]

    def load_pdf(self):
        pdf_path = filedialog.askopenfilename(title="Select Contract PDF", filetypes=[("PDF Files", "*.pdf")])
        if not pdf_path: return
        
        self.status_lbl.configure(text="Reading PDF...")
        self.log_to_console("--- Starting Batch PDF Ingestion ---")
        self.log_to_console(f"Selected: {os.path.basename(pdf_path)}")
        self.progress_bar.start()
        
        # Start matching pipeline in thread
        threading.Thread(target=self._process_pdf, args=(pdf_path,), daemon=True).start()

    def _process_pdf(self, pdf_path):
        try:
            ms = matching_engine.MatchService(self.master.catalog, llm_model=ConfigManager.get("llm_model"))
            
            # ── Safety Check: Is Ollama up? ──────────────────────────────
            if self.winfo_exists():
                self.after(0, lambda: self.status_lbl.configure(text="🔍 Checking AI service..."))
            self.log_to_console("Checking AI service...")
            
            ready, err = ms.check_ollama_ready()
            if not ready:
                if self.winfo_exists():
                    self.after(0, lambda: messagebox.showerror("Ollama Connection Error", 
                        f"AI service is not responding.\n\n{err}\n\nPlease ensure Ollama is running."))
                    self.after(0, lambda: self.status_lbl.configure(text="❌ Ollama Offline."))
                self.log_to_console("Error: Ollama Offline.")
                return

            self.log_to_console("Extracting text from PDF... (this may take a moment)")
            ingestor = OneClickIngestor(pdf_path)
            data = ingestor.extract_data()
            
            if "line_items" not in data or not data["line_items"]:
                if self.winfo_exists():
                    self.after(0, lambda: messagebox.showwarning("Warning", "No readable items found in PDF."))
                    self.after(0, lambda: self.status_lbl.configure(text=""))
                self.log_to_console("Error: No items found in PDF.")
                return
                
            num_items = len(data["line_items"])
            self.log_to_console(f"Found {num_items} items in PDF. Starting matching pipeline...")
                
            ms = matching_engine.MatchService(self.master.catalog, llm_model=ConfigManager.get("llm_model"))
            
            def update_progress(current, total):
                if self.winfo_exists() and self.status_lbl.winfo_exists():
                    self.after(0, lambda: self.status_lbl.configure(text=f"Extracting item {current} of {total} with LLM..."))
                    
            def status_cb(msg):
                self.log_to_console(msg)
                
            enriched = ms.enrich_items(data["line_items"], progress_callback=update_progress, status_callback=status_cb)
            
            self.unmatched_items = []
            for it in enriched:
                score_color = it.get("_match", {}).get("color_code", "red")
                if score_color != "green" and not it.get("_match", {}).get("is_ignored"):
                    # Avoid duplicates
                    if it["raw_description"] not in [x["raw_description"] for x in self.unmatched_items]:
                        self.unmatched_items.append(it)
                        
            if self.winfo_exists():
                self.after(0, self._render_queue)
                
        except Exception as e:
            self.log_to_console(f"Error during ingestion: {str(e)}")
        finally:
            if self.winfo_exists() and self.progress_bar.winfo_exists():
                self.after(0, self.progress_bar.stop)
                self.after(0, lambda: self.progress_bar.set(0))
        
    def _render_queue(self):
        self.status_lbl.configure(text=f"Found {len(self.unmatched_items)} unmatched items.")
        
        for w in self.queue_frame.winfo_children():
            w.destroy()
            
        for idx, item in enumerate(self.unmatched_items):
            desc = item["raw_description"]
            display_desc = desc if len(desc) < 40 else desc[:37] + "..."
            
            btn = ctk.CTkButton(
                self.queue_frame, 
                text=display_desc, 
                fg_color="gray20",
                hover_color="gray30",
                anchor="w",
                command=lambda it=item: self.select_item(it)
            )
            btn.pack(fill="x", padx=5, pady=2)

    def select_item(self, item):
        self.selected_raw_text = item.get("raw_description", "")
        
        # Clear fields
        self.id_entry.delete(0, 'end')
        self.brand_entry.delete(0, 'end')
        self.oneclick_entry.delete(0, 'end')
        self.finish_entry.delete(0, 'end')
        self.desc_entry.delete(0, 'end')
        for w in self.dimensions_frame.winfo_children():
            w.destroy()
        self.dimension_rows = []
        self.image_path_var.set("")
        self.routing_entry.set("WAREHOUSE")
        
        self.oneclick_entry.insert(0, self.selected_raw_text)
        
        extracted = item.get("_match", {}).get("extracted_fields")
        if extracted:
            self._fill_fields(extracted)
            self.status_lbl.configure(text="Loaded fields from session cache.")
        else:
            self.status_lbl.configure(text="Querying LLM for details...")
            self.progress_bar.start()
            threading.Thread(target=self._query_llm_fields, args=(self.selected_raw_text,), daemon=True).start()

    def _query_llm_fields(self, text):
        try:
            # ── Safety Check ──
            ready, err = self.llm_client.check_connection()
            if not ready:
                self.after(0, lambda: messagebox.showerror("Ollama Connection Error", f"Cannot extract fields: {err}"))
                return

            res = self.llm_client.extract_product_fields(text)
            self.after(0, lambda: self._fill_fields(res))
            self.after(0, lambda: self.status_lbl.configure(text="Done."))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("LLM Error", str(e)))
            self.after(0, lambda: self.status_lbl.configure(text=""))
        finally:
            self.after(0, self.progress_bar.stop)
            self.after(0, lambda: self.progress_bar.set(0))
            
    def _fill_fields(self, res):
        b = res.get("brand", "")
        if b: self.brand_entry.insert(0, b)
        
        c = res.get("category", "")
        if c: 
            # Best effort Category guess
            cat_list = self.cat_entry.cget("values")
            b_cat = next((x for x in cat_list if c.lower() in x.lower()), None)
            if b_cat: self.cat_entry.set(b_cat)
            
        f = res.get("finish", "")
        if f: self.finish_entry.insert(0, f)
        
        d = res.get("description", "")
        if d: self.desc_entry.insert(0, d)
        
        dims = res.get("dimensions", {})
        for k, v in dims.items():
            if v and str(v).strip() and str(v).lower() not in ["unknown", "n/a", "none"]:
                self.add_dimension_row(k, v)

    def initiate_save(self):
        if not self.id_entry.get().strip() or not self.cat_entry.get().strip():
            messagebox.showwarning("Incomplete", "ID and Category are required.")
            return
            
        self._save_to_yaml()

    def _save_to_yaml(self):
        cat_file = self.cat_entry.get().strip()

        target_id = self.id_entry.get().strip()
        existing_item = self.master.catalog.get(target_id)

        sku           = existing_item.get("sku", "MISSING_SKU") if existing_item else "MISSING_SKU"
        provider      = existing_item.get("provider", "MISSING_PROVIDER") if existing_item else "MISSING_PROVIDER"
        purchase_link = existing_item.get("purchase_link", "") if existing_item else ""

        product = {
            "id": target_id,
            "sku": sku,
            "brand": self.brand_entry.get().strip(),
            "provider": provider,
            "purchase_link": purchase_link,
            "routing_tag": self.routing_entry.get().strip(),
            "oneclick_description": self.oneclick_entry.get().strip(),
            "printable": {
                "finish": self.finish_entry.get().strip(),
                "description": self.desc_entry.get().strip(),
                "dimensions": ProductService.read_dimension_rows(self.dimension_rows),
            }
        }

        source_image_path = self.image_path_var.get()
        if source_image_path:
            product["printable"]["image_file"] = ProductService.copy_image_to_assets(
                source_image_path, self.assets_path
            )

        ProductService.upsert_to_yaml(product, cat_file, self.categories_path)

        messagebox.showinfo("Success", f"Saved {product['id']} successfully!")

        # Remove from queue visually
        if self.selected_raw_text:
            self.unmatched_items = [x for x in self.unmatched_items if x["raw_description"] != self.selected_raw_text]
            self._render_queue()

        if self.refresh_callback:
            self.refresh_callback()

        # Push catalog update
        self.master.catalog = self.db_loader.load_all_categories()
        if hasattr(self.master, 'refresh_match_service'):
            self.master.refresh_match_service()
        elif hasattr(self.master, 'master') and hasattr(self.master.master, 'refresh_match_service'):
            self.master.master.refresh_match_service()

class DatabasePicker(ctk.CTkToplevel):
    def __init__(self, master, catalog, callback):
        super().__init__(master)
        self.title("Pick Product from Database")
        self.geometry("800x600")
        self.transient(master)
        self.grab_set()
        self.focus_set()
        
        self.catalog = catalog
        self.callback = callback
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Search Frame
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        search_frame.grid_columnconfigure(0, weight=1)
        
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search by ID, SKU, or Description...")
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_list())
        
        # List Frame
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        
        self.refresh_list()
        
    def refresh_list(self):
        for w in self.scroll_frame.winfo_children():
            w.destroy()
            
        query = self.search_entry.get().lower()
        
        for item_id, item in self.catalog.items():
            sku = item.get("sku", "").lower()
            desc = item.get("oneclick_description", "").lower()
            
            if query in item_id.lower() or query in sku or query in desc:
                btn_text = f"[{item_id}] | SKU: {item.get('sku')} | {item.get('oneclick_description')[:60]}"
                btn = ctk.CTkButton(
                    self.scroll_frame, 
                    text=btn_text, 
                    anchor="w", 
                    fg_color="transparent",
                    text_color=("gray10", "gray90"),
                    hover_color=("gray70", "gray30"),
                    command=lambda it=item: self.select_item(it)
                )
                btn.pack(fill="x", padx=5, pady=2)
                
    def select_item(self, item):
        self.callback(item)
        self.destroy()
