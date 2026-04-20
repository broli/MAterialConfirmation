import customtkinter as ctk
import tkinter.messagebox as messagebox
from tkinter import filedialog
import os
import yaml
import shutil
import threading
from PIL import Image

from contract_ingestion import OneClickIngestor
import matching_engine
from llm_service import LocalLLMClient

class BatchPdfIngestWindow(ctk.CTkToplevel):
    def __init__(self, master, db_loader, categories_path, assets_path, refresh_callback):
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
        self.unmatched_items = []
        self.selected_raw_text = ""
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)
        
        self.build_left_pane()
        self.build_right_pane()
        
    def build_left_pane(self):
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.left_frame.grid_rowconfigure(2, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.left_frame, text="1. Select Job Folder", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, pady=(10, 5), padx=10, sticky="w")
        ctk.CTkButton(self.left_frame, text="Browse for Estimate...", command=self.load_pdf).grid(row=1, column=0, pady=5, padx=10, sticky="ew")
        
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
        
        ctk.CTkLabel(self.right_frame, text="2. Modify extracted details", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=(10, 20), sticky="w")
        
        # Identity
        ctk.CTkLabel(self.right_frame, text="Category File *").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.cat_entry = ctk.CTkComboBox(self.right_frame, values=self._get_existing_categories())
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
        
        # Printable attributes
        ctk.CTkLabel(self.right_frame, text="Finish (Color)").grid(row=5, column=0, padx=10, pady=5, sticky="e")
        self.finish_entry = ctk.CTkEntry(self.right_frame)
        self.finish_entry.grid(row=5, column=1, padx=10, pady=5, sticky="ew")
        
        ctk.CTkLabel(self.right_frame, text="Marketing Description").grid(row=6, column=0, padx=10, pady=5, sticky="e")
        self.desc_entry = ctk.CTkEntry(self.right_frame)
        self.desc_entry.grid(row=6, column=1, padx=10, pady=5, sticky="ew")
        
        # Dimensions
        dim_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        dim_frame.grid(row=7, column=1, padx=10, pady=5, sticky="ew")
        self.w_entry = ctk.CTkEntry(dim_frame, placeholder_text="Width (e.g. 16\")", width=120)
        self.w_entry.pack(side="left", padx=(0,5))
        self.h_entry = ctk.CTkEntry(dim_frame, placeholder_text="Height", width=120)
        self.h_entry.pack(side="left", padx=5)
        self.d_entry = ctk.CTkEntry(dim_frame, placeholder_text="Depth", width=120)
        self.d_entry.pack(side="left", padx=5)
        
        # Action
        self.btn_compile = ctk.CTkButton(self.right_frame, text="Compile Rules & Save", fg_color="green", command=self.initiate_save)
        self.btn_compile.grid(row=8, column=0, columnspan=2, pady=30)
        
        # Info label
        self.status_lbl = ctk.CTkLabel(self.right_frame, text="", text_color="yellow")
        self.status_lbl.grid(row=9, column=0, columnspan=2)

        # Terminal output stick to bottom
        self.console_container = ctk.CTkFrame(self.right_container, fg_color="transparent")
        self.console_container.grid(row=1, column=0, sticky="nsew")
        self.console_container.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(self.console_container, mode="indeterminate")
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.progress_bar.set(0)

        ctk.CTkLabel(self.console_container, text="Terminal Log", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, pady=(0, 2), sticky="w")
        self.console_box = ctk.CTkTextbox(self.console_container, height=150, fg_color="black", text_color="#00FF00", font=ctk.CTkFont(family="Courier", size=11))
        self.console_box.grid(row=2, column=0, sticky="ew")
        self.console_box.configure(state="disabled")

    def log_to_console(self, msg):
        def _update():
            self.console_box.configure(state="normal")
            self.console_box.insert("end", msg + "\n")
            self.console_box.see("end")
            self.console_box.configure(state="disabled")
        self.after(0, _update)

    def _get_existing_categories(self):
        if not os.path.exists(self.categories_path): return []
        return [f for f in os.listdir(self.categories_path) if f.endswith('.yaml')]

    def load_pdf(self):
        dirpath = filedialog.askdirectory(title="Select Job Folder with PDF")
        if not dirpath: return
        
        self.status_lbl.configure(text="Reading PDF...")
        # Start matching pipeline in thread
        threading.Thread(target=self._process_pdf, args=(dirpath,), daemon=True).start()

    def _process_pdf(self, dirpath):
        ingestor = OneClickIngestor(dirpath)
        data = ingestor.extract_data()
        
        if "line_items" not in data or not data["line_items"]:
            self.after(0, lambda: messagebox.showwarning("Warning", "No readable items found in PDF."))
            self.after(0, lambda: self.status_lbl.configure(text=""))
            return
            
        ms = matching_engine.MatchService(self.master.catalog)
        enriched = ms.enrich_items(data["line_items"])
        
        self.unmatched_items = []
        for it in enriched:
            score_color = it.get("_match", {}).get("color_code", "red")
            if score_color != "green" and not it.get("_match", {}).get("is_ignored"):
                # Avoid duplicates
                if it["raw_description"] not in [x["raw_description"] for x in self.unmatched_items]:
                    self.unmatched_items.append(it)
                
        self.after(0, self._render_queue)
        
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
                command=lambda d=desc: self.select_item(d)
            )
            btn.pack(fill="x", padx=5, pady=2)

    def select_item(self, raw_text):
        self.selected_raw_text = raw_text
        self.status_lbl.configure(text="Querying LLM for details...")
        
        # Clear fields
        self.id_entry.delete(0, 'end')
        self.brand_entry.delete(0, 'end')
        self.oneclick_entry.delete(0, 'end')
        self.finish_entry.delete(0, 'end')
        self.desc_entry.delete(0, 'end')
        self.w_entry.delete(0, 'end')
        self.h_entry.delete(0, 'end')
        self.d_entry.delete(0, 'end')
        
        self.oneclick_entry.insert(0, raw_text)
        
        self.progress_bar.start()
        threading.Thread(target=self._query_llm_fields, args=(raw_text,), daemon=True).start()

    def _query_llm_fields(self, text):
        try:
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
        if dims.get("width"): self.w_entry.insert(0, dims.get("width"))
        if dims.get("height"): self.h_entry.insert(0, dims.get("height"))
        if dims.get("depth"): self.d_entry.insert(0, dims.get("depth"))

    def initiate_save(self):
        if not self.id_entry.get().strip() or not self.cat_entry.get().strip():
            messagebox.showwarning("Incomplete", "ID and Category are required.")
            return
            
        self.status_lbl.configure(text="Compiling strict Matching Rules with LLM...")
        self.btn_compile.configure(state="disabled")
        
        # Build dictionary
        prod = {
            "id": self.id_entry.get().strip(),
            "brand": self.brand_entry.get().strip(),
            "finish": self.finish_entry.get().strip(),
            "dimensions": {
                "width": self.w_entry.get().strip(),
                "height": self.h_entry.get().strip(),
                "depth": self.d_entry.get().strip()
            }
        }
        
        self.progress_bar.start()
        threading.Thread(target=self._compile_and_confirm, args=(prod,), daemon=True).start()

    def _compile_and_confirm(self, prod):
        try:
            rules = self.llm_client.compile_matching_rules(prod)
            self.after(0, lambda: self._show_confirmation_window(rules))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("LLM Error compiling rules", str(e)))
            self.after(0, lambda: self.btn_compile.configure(state="normal"))
            self.after(0, lambda: self.status_lbl.configure(text=""))
        finally:
            self.after(0, self.progress_bar.stop)
            self.after(0, lambda: self.progress_bar.set(0))

    def _show_confirmation_window(self, rules):
        self.btn_compile.configure(state="normal")
        self.status_lbl.configure(text="")
        
        conf_msg = "LLM compiled the following regex rules for this item:\n\n"
        conf_msg += "MUST CONTAIN:\n" + "\n".join(rules.get('must_contain_regex', [])) + "\n\n"
        conf_msg += "MUST NOT CONTAIN:\n" + "\n".join(rules.get('must_not_contain_regex', [])) + "\n\n"
        conf_msg += "Are you completely satisfied and ready to commit to the YAML Database?"
        
        if messagebox.askyesno("Confirm Final Rules", conf_msg):
            self._save_to_yaml(rules)

    def _save_to_yaml(self, rules):
        cat_file = self.cat_entry.get().strip()
        
        product = {
            "id": self.id_entry.get().strip(),
            "sku": "MISSING_SKU",
            "brand": self.brand_entry.get().strip(),
            "provider": "MISSING_PROVIDER",
            "routing_tag": "WAREHOUSE",
            "oneclick_description": self.oneclick_entry.get().strip(),
            "matching_rules": rules,
            "printable": {
                "finish": self.finish_entry.get().strip(),
                "description": self.desc_entry.get().strip(),
                "dimensions": {}
            }
        }
        
        if self.w_entry.get().strip(): product["printable"]["dimensions"]["width"] = self.w_entry.get().strip()
        if self.h_entry.get().strip(): product["printable"]["dimensions"]["height"] = self.h_entry.get().strip()
        if self.d_entry.get().strip(): product["printable"]["dimensions"]["depth"] = self.d_entry.get().strip()

        target_yaml_path = os.path.join(self.categories_path, cat_file)
        existing_data = []
        if os.path.exists(target_yaml_path):
            with open(target_yaml_path, 'r', encoding='utf-8') as f:
                existing_data = yaml.safe_load(f) or []
                
        existing_data = [i for i in existing_data if i.get('id') != product["id"]]
        existing_data.append(product)

        with open(target_yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(existing_data, f, sort_keys=False, allow_unicode=True)

        messagebox.showinfo("Success", f"Saved {product['id']} successfully!")
        
        # Remove from queue visually
        if self.selected_raw_text:
            self.unmatched_items = [x for x in self.unmatched_items if x["raw_description"] != self.selected_raw_text]
            self._render_queue()
            
        if self.refresh_callback:
            self.refresh_callback()
            
        # Push catalog update
        self.master.catalog = self.db_loader.load_all_categories()
        if hasattr(self.master.master, 'refresh_match_service'):
            self.master.master.refresh_match_service()
