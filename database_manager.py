import customtkinter as ctk
import tkinter.messagebox as messagebox
from tkinter import filedialog
import os
import yaml
import shutil
import csv
from PIL import Image
from product_service import ProductService

class DatabaseManager(ctk.CTkToplevel):
    def __init__(self, master, db_loader):
        super().__init__(master)
        
        self.title("Catalog Manager")
        
        # Load window geometry from config
        from config_manager import ConfigManager
        width = ConfigManager.get("db_window_width")
        height = ConfigManager.get("db_window_height")
        x = ConfigManager.get("db_window_x")
        y = ConfigManager.get("db_window_y")
        is_maximized = ConfigManager.get("db_window_maximized")

        self.geometry(f"{width}x{height}+{x}+{y}")
        if is_maximized:
            self.after(200, lambda: self.state('zoomed'))

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.grab_set()
        self.focus_set()
        self.attributes("-topmost", True)

        self.db_loader = db_loader
        self.categories_path = os.path.join(self.db_loader.base_path, "categories")
        self.assets_path = os.path.join(self.db_loader.base_path, "assets")

        self.catalog = self.db_loader.load_all_categories()
        
        self.editing_item_id = None
        self.editing_original_cat = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.admin_container = ctk.CTkFrame(self, fg_color="transparent")
        self.admin_container.grid(row=0, column=0, sticky="nsew")
        self.admin_container.grid_columnconfigure(0, weight=1)
        self.admin_container.grid_rowconfigure(0, weight=1) 

        self.build_browser_view()
        self.build_form_view()
        self.show_browser_view()
        
        self.after(100, lambda: self.attributes("-topmost", False))

    def get_unique_values(self, key):
        values = set()
        for item in self.catalog.values():
            if key == 'finish':
                if 'printable' in item and 'finish' in item['printable']:
                    val = item['printable']['finish']
                    if val: values.add(val)
            else:
                if key in item and item[key]:
                    values.add(item[key])
        return sorted(list(values))

    def get_existing_categories(self):
        if not os.path.exists(self.categories_path):
            return ["faucets.yaml", "vanities.yaml"] 
        return [f for f in os.listdir(self.categories_path) if f.endswith('.yaml')]

    # --- View 1: Database Browser ---
    def build_browser_view(self):
        self.browser_frame = ctk.CTkFrame(self.admin_container, fg_color="transparent")
        self.browser_frame.grid_columnconfigure(0, weight=1)
        self.browser_frame.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.browser_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(header, text="Database Browser", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=20)
        
        ctk.CTkButton(header, text="Add New Item", command=self.show_form_view, fg_color="green", hover_color="darkgreen").pack(side="right", padx=20)

        self.tree_frame = ctk.CTkScrollableFrame(self.browser_frame)
        self.tree_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

    def refresh_browser_list(self):
        for widget in self.tree_frame.winfo_children():
            widget.destroy()

        if not os.path.exists(self.categories_path):
            return

        txt_color = ctk.ThemeManager.theme["CTkLabel"]["text_color"]

        for cat_file in os.listdir(self.categories_path):
            if not cat_file.endswith('.yaml'): continue
            
            cat_header = ctk.CTkLabel(self.tree_frame, text=f"📁 {cat_file.upper()}", font=ctk.CTkFont(weight="bold", size=14), text_color="#00BFFF")
            cat_header.pack(anchor="w", pady=(15, 2), padx=5)
            
            file_path = os.path.join(self.categories_path, cat_file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    items = yaml.safe_load(f) or []
                    for item in items:
                        desc = item.get('oneclick_description', '')
                        if len(desc) > 80: desc = desc[:77] + "..."
                        text = f"  ├─ [{item.get('id')}] : {item.get('sku')} | {desc}"
                        
                        btn = ctk.CTkButton(self.tree_frame, text=text, font=ctk.CTkFont(family="Courier", size=12),
                                            fg_color="transparent", text_color=txt_color,
                                            hover_color=("gray70", "gray30"), anchor="w",
                                            command=lambda idx=item.get('id'): self.view_product_details(idx))
                        btn.pack(anchor="w", padx=10, fill="x")
            except Exception:
                pass

    # --- View 1.5: Product Details ---
    def view_product_details(self, item_id):
        item = self.catalog.get(item_id)
        if not item: return

        top = ctk.CTkToplevel(self)
        top.title(f"Product Details - {item_id}")
        top.geometry("500x700")
        top.transient(self)
        top.grab_set()
        top.focus_set()
        top.attributes("-topmost", True)

        printable = item.get("printable", {})
        
        img_file = printable.get("image_file")
        if img_file:
            img_path = os.path.join(self.assets_path, img_file)
            if os.path.exists(img_path):
                try:
                    pil_img = Image.open(img_path)
                    pil_img.thumbnail((300, 300))
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                    lbl_img = ctk.CTkLabel(top, image=ctk_img, text="")
                    lbl_img.pack(pady=15)
                except Exception as e:
                    ctk.CTkLabel(top, text=f"[ Image Error: {e} ]", text_color="red").pack(pady=10)
        
        details = f"ID: {item_id}\n"
        details += f"Category File: {item.get('category_file', 'N/A')}.yaml\n\n"
        details += f"SKU: {item.get('sku')}\n"
        details += f"Brand: {item.get('brand')}\n"
        details += f"Provider: {item.get('provider')}\n"
        details += f"Routing: {item.get('routing_tag')}\n"
        
        link_preview = item.get('purchase_link', 'None')
        if len(link_preview) > 80: link_preview = link_preview[:77] + "..."
        details += f"Purchase Link: {link_preview}\n"
        
        desc_preview = item.get('oneclick_description', '')
        if len(desc_preview) > 80: desc_preview = desc_preview[:77] + "..."
        details += f"OneClick Desc: {desc_preview}\n"
        
        if printable:
            details += f"\n--- Client Printable ---\n"
            details += f"Finish: {printable.get('finish')}\n"
            dims = printable.get("dimensions", {})
            if dims:
                dim_str = ", ".join([f"{k}: {v}" for k, v in dims.items()])
                details += f"Dimensions: {dim_str}\n"

        lbl_details = ctk.CTkLabel(top, text=details, justify="left", font=ctk.CTkFont(size=14), wraplength=460)
        lbl_details.pack(pady=5, padx=20, anchor="w")

        desc = ctk.CTkTextbox(top, height=80, width=460)
        desc.insert("0.0", printable.get("description", "No description (or hidden)"))
        desc.configure(state="disabled")
        desc.pack(pady=10, padx=20)

        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.pack(side="bottom", pady=20, fill="x", padx=20)

        btn_edit = ctk.CTkButton(btn_frame, text="Edit Product", fg_color="#153E83", hover_color="#0d2b61",
                                 command=lambda: self.load_for_edit(item_id, top))
        btn_edit.pack(side="left", expand=True, padx=5)

        btn_duplicate = ctk.CTkButton(btn_frame, text="Duplicate Product", fg_color="gray20", hover_color="gray30",
                                      command=lambda: self.duplicate_product(item_id, top))
        btn_duplicate.pack(side="left", expand=True, padx=5)

        btn_delete = ctk.CTkButton(btn_frame, text="Delete Product", fg_color="red", hover_color="darkred",
                                   command=lambda: self.delete_product(item_id, top))
        btn_delete.pack(side="right", expand=True, padx=5)

    def duplicate_product(self, item_id, window):
        window.destroy()
        item = self.catalog.get(item_id)
        if not item: return

        self.show_form_view()
        self.editing_item_id = None
        self.editing_original_cat = None
        self.form_header_label.configure(text=f"Duplicating Product: {item_id}")

        self.cat_combobox.set(item.get('category_file') + '.yaml')
        self.id_entry.delete(0, 'end')
        self.sku_entry.insert(0, item.get('sku', ''))
        self.brand_combobox.set(item.get('brand', ''))
        self.provider_combobox.set(item.get('provider', ''))
        self.routing_combobox.set(item.get('routing_tag', ''))
        self.purchase_link_entry.insert(0, item.get('purchase_link', ''))
        self.oneclick_entry.insert(0, item.get('oneclick_description', ''))
        
        printable = item.get("printable", {})
        if printable:
            self.printable_checkbox_var.set(True)
            self.finish_combobox.set(printable.get('finish', ''))
            dims = printable.get('dimensions', {})
            for k, v in dims.items():
                self.add_dimension_row(k, v)
            
            self.desc_entry.delete("0.0", "end")
            self.desc_entry.insert("0.0", printable.get('description', ''))
            
            if printable.get('image_file'):
                abs_img_path = os.path.abspath(os.path.join(self.assets_path, printable.get('image_file')))
                if os.path.exists(abs_img_path):
                    self.image_path_var.set(abs_img_path)
        else:
            self.printable_checkbox_var.set(False)

    def load_for_edit(self, item_id, window):
        window.destroy()
        item = self.catalog.get(item_id)
        if not item: return

        self.show_form_view()
        self.editing_item_id = item_id
        self.editing_original_cat = item.get('category_file') + '.yaml'
        self.form_header_label.configure(text=f"Editing Product: {item_id}")

        self.cat_combobox.set(self.editing_original_cat)
        self.id_entry.insert(0, item.get('id', ''))
        self.sku_entry.insert(0, item.get('sku', ''))
        self.brand_combobox.set(item.get('brand', ''))
        self.provider_combobox.set(item.get('provider', ''))
        self.routing_combobox.set(item.get('routing_tag', ''))
        self.purchase_link_entry.insert(0, item.get('purchase_link', ''))
        self.oneclick_entry.insert(0, item.get('oneclick_description', ''))
        
        printable = item.get("printable", {})
        if printable:
            self.printable_checkbox_var.set(True)
            self.finish_combobox.set(printable.get('finish', ''))
            dims = printable.get('dimensions', {})
            for k, v in dims.items():
                self.add_dimension_row(k, v)
            
            self.desc_entry.delete("0.0", "end")
            self.desc_entry.insert("0.0", printable.get('description', ''))
            
            if printable.get('image_file'):
                abs_img_path = os.path.abspath(os.path.join(self.assets_path, printable.get('image_file')))
                if os.path.exists(abs_img_path):
                    self.image_path_var.set(abs_img_path)
        else:
            self.printable_checkbox_var.set(False)

    def delete_product(self, item_id, window=None):
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to permanently delete ID: {item_id}?")
        if not confirm: return

        item = self.catalog.get(item_id)
        cat_file = item.get('category_file') + '.yaml'

        ProductService.remove_from_yaml(item_id, cat_file, self.categories_path)

        self.catalog = self.db_loader.load_all_categories()
        self.master.catalog = self.db_loader.load_all_categories()
        self.refresh_browser_list()

        if window:
            window.destroy()
        messagebox.showinfo("Deleted", f"Product {item_id} has been removed.")

    # --- View 2: Add / Edit Form ---
    def build_form_view(self):
        self.form_frame = ctk.CTkScrollableFrame(self.admin_container, fg_color="transparent")
        self.form_frame.grid_columnconfigure((0, 1), weight=1)

        header = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        ctk.CTkButton(header, text="← Back", command=self.show_browser_view, width=60).pack(side="left")
        
        self.form_header_label = ctk.CTkLabel(header, text="Add New Product", font=ctk.CTkFont(size=18, weight="bold"))
        self.form_header_label.pack(side="left", padx=20)

        # Identity & Matching (Internal)
        ctk.CTkLabel(self.form_frame, text="INTERNAL MATCHING LOGIC", font=ctk.CTkFont(weight="bold", size=14), text_color="#00BFFF").grid(row=1, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w")
        
        ctk.CTkLabel(self.form_frame, text="Category File *", anchor="w").grid(row=2, column=0, padx=10, sticky="ew")
        self.cat_combobox = ctk.CTkComboBox(self.form_frame, values=self.get_existing_categories(), command=self.on_category_change)
        self.cat_combobox.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(self.form_frame, text="Unique ID *", text_color="yellow", anchor="w").grid(row=2, column=1, padx=10, sticky="ew")
        self.id_entry = ctk.CTkEntry(self.form_frame)
        self.id_entry.grid(row=3, column=1, padx=10, pady=(0, 10), sticky="ew")
        
        ctk.CTkLabel(self.form_frame, text="SKU *", text_color="yellow", anchor="w").grid(row=4, column=0, padx=10, sticky="ew")
        self.sku_entry = ctk.CTkEntry(self.form_frame)
        self.sku_entry.grid(row=5, column=0, padx=10, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(self.form_frame, text="OneClick Description * (REQUIRED FOR MATCHING)", anchor="w", text_color="yellow").grid(row=4, column=1, padx=10, sticky="ew")
        self.oneclick_entry = ctk.CTkEntry(self.form_frame)
        self.oneclick_entry.grid(row=5, column=1, padx=10, pady=(0, 10), sticky="ew")

        # ERP Routing Ops
        ctk.CTkLabel(self.form_frame, text="ERP ROUTING & DISPATCH", font=ctk.CTkFont(weight="bold", size=14), text_color="#00BFFF").grid(row=6, column=0, columnspan=2, padx=10, pady=(20, 5), sticky="w")

        ctk.CTkLabel(self.form_frame, text="Brand", anchor="w").grid(row=7, column=0, padx=10, sticky="ew")
        self.brand_combobox = ctk.CTkComboBox(self.form_frame, values=self.get_unique_values('brand'))
        self.brand_combobox.grid(row=8, column=0, padx=10, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(self.form_frame, text="Routing Tag *", text_color="yellow", anchor="w").grid(row=7, column=1, padx=10, sticky="ew")
        self.routing_combobox = ctk.CTkComboBox(self.form_frame, values=["IGNORE", "WAREHOUSE", "PROCURE", "WH_OR_PROCURE"])
        self.routing_combobox.grid(row=8, column=1, padx=10, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(self.form_frame, text="Provider", anchor="w").grid(row=9, column=0, padx=10, sticky="ew")
        self.provider_combobox = ctk.CTkComboBox(self.form_frame, values=self.get_unique_values('provider'))
        self.provider_combobox.grid(row=10, column=0, padx=10, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(self.form_frame, text="Purchase Link / Action", anchor="w").grid(row=9, column=1, padx=10, sticky="ew")
        self.purchase_link_entry = ctk.CTkEntry(self.form_frame)
        self.purchase_link_entry.grid(row=10, column=1, padx=10, pady=(0, 10), sticky="ew")

        # Printable Section
        ctk.CTkLabel(self.form_frame, text="CLIENT DISPLAY BLOCK", font=ctk.CTkFont(weight="bold", size=14), text_color="#00BFFF").grid(row=11, column=0, columnspan=2, padx=10, pady=(20, 5), sticky="w")
        self.printable_checkbox_var = ctk.BooleanVar(value=True)
        self.printable_checkbox = ctk.CTkCheckBox(self.form_frame, text="Is Client Facing (Will generate printable block)", variable=self.printable_checkbox_var)
        self.printable_checkbox.grid(row=12, column=0, columnspan=2, padx=10, pady=(5, 5), sticky="w")

        self.printable_frame = ctk.CTkFrame(self.form_frame)
        self.printable_frame.grid(row=13, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        
        ctk.CTkLabel(self.printable_frame, text="Finish", anchor="w").grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        
        existing_finishes = self.get_unique_values('finish')
        if not existing_finishes: existing_finishes = ["Chrome", "Matte Black", "Brushed Nickel", "White"]
        self.finish_combobox = ctk.CTkComboBox(self.printable_frame, values=existing_finishes)
        self.finish_combobox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

        # Dynamic Dimensions Frame
        self.dimension_rows = []
        
        dim_header_frame = ctk.CTkFrame(self.printable_frame, fg_color="transparent")
        dim_header_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky="ew", padx=10)
        ctk.CTkLabel(dim_header_frame, text="Dimensions", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)
        ctk.CTkButton(dim_header_frame, text="+ Add Measurement", width=120, command=self.add_dimension_row).pack(side="right", padx=10)

        self.dimensions_frame = ctk.CTkFrame(self.printable_frame)
        self.dimensions_frame.grid(row=3, column=0, columnspan=2, pady=(5, 10), sticky="ew", padx=10)

        ctk.CTkLabel(self.printable_frame, text="Marketing Description", anchor="w").grid(row=4, column=0, columnspan=2, padx=10, sticky="ew")
        self.desc_entry = ctk.CTkTextbox(self.printable_frame, height=60)
        self.desc_entry.grid(row=5, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")

        self.image_path_var = ctk.StringVar(value="")
        img_frame = ctk.CTkFrame(self.printable_frame, fg_color="transparent")
        img_frame.grid(row=6, column=0, columnspan=2, pady=10, sticky="ew", padx=10)
        ctk.CTkButton(img_frame, text="Browse Image...", command=self.browse_image).pack(side="left", padx=10)
        ctk.CTkLabel(img_frame, textvariable=self.image_path_var).pack(side="left")

        ctk.CTkButton(self.form_frame, text="Save to Database", command=self.save_product, fg_color="blue", height=40).grid(row=14, column=0, columnspan=2, pady=20)

    def add_dimension_row(self, key="", value=""):
        """Add one dimension input row. Delegates to ProductService helper."""
        ProductService.build_dimension_rows(
            self.dimensions_frame,
            existing_dims={key: value} if key else {},
            row_store=self.dimension_rows,
        )

    # --- View Switchers ---
    def show_browser_view(self):
        self.form_frame.grid_forget()
        self.browser_frame.grid(row=0, column=0, sticky="nsew")
        self.refresh_browser_list()

    def show_form_view(self):
        self.browser_frame.grid_forget()
        self.form_frame.grid(row=0, column=0, sticky="nsew")
        
        self.editing_item_id = None
        self.editing_original_cat = None
        self.form_header_label.configure(text="Add New Product")

        self.brand_combobox.configure(values=self.get_unique_values('brand'))
        self.provider_combobox.configure(values=self.get_unique_values('provider'))
        
        existing_finishes = self.get_unique_values('finish')
        if not existing_finishes: existing_finishes = ["Chrome", "Matte Black", "Brushed Nickel", "White"]
        self.finish_combobox.configure(values=existing_finishes)
        
        self.cat_combobox.configure(values=self.get_existing_categories())

        if self.get_existing_categories():
            self.cat_combobox.set(self.get_existing_categories()[0]) 
            
        self.id_entry.delete(0, 'end')
        self.sku_entry.delete(0, 'end')
        self.purchase_link_entry.delete(0, 'end')
        self.oneclick_entry.delete(0, 'end')
        for w in self.dimensions_frame.winfo_children():
            w.destroy()
        self.dimension_rows = []
        self.desc_entry.delete("0.0", "end")
        self.image_path_var.set("")
        self.printable_checkbox_var.set(True)

    # --- Form Actions ---
    def browse_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.jpeg *.png")])
        if file_path:
            self.image_path_var.set(file_path)

    def on_closing(self):
        # Save window state before exiting
        from config_manager import ConfigManager
        is_maximized = (self.state() == 'zoomed')
        ConfigManager.set("db_window_maximized", is_maximized)
        
        if not is_maximized:
            ConfigManager.set("db_window_width", self.winfo_width())
            ConfigManager.set("db_window_height", self.winfo_height())
            ConfigManager.set("db_window_x", self.winfo_x())
            ConfigManager.set("db_window_y", self.winfo_y())
            
        self.destroy()

    def on_category_change(self, choice):
        if choice == "ignore.yaml":
            if not self.id_entry.get().strip():
                next_id = self.db_loader.get_next_ignore_id()
                self.id_entry.insert(0, next_id)

    def save_product(self):
        cat_file = self.cat_combobox.get().strip()
        if not cat_file.endswith(".yaml"):
            cat_file += ".yaml"

        product = {
            "id": self.id_entry.get().strip(),
            "sku": self.sku_entry.get().strip(),
            "brand": self.brand_combobox.get().strip(),
            "provider": self.provider_combobox.get().strip(),
            "routing_tag": self.routing_combobox.get().strip(),
            "purchase_link": self.purchase_link_entry.get().strip(),
            "oneclick_description": self.oneclick_entry.get().strip(),
        }

        if not product["id"] or not product["sku"] or not product["oneclick_description"]:
            messagebox.showwarning("Incomplete Data", "ID, SKU, and OneClick Description are required.")
            return

        if self.printable_checkbox_var.get():
            printable = {
                "finish": self.finish_combobox.get().strip(),
                "description": self.desc_entry.get("0.0", "end").strip(),
                "dimensions": ProductService.read_dimension_rows(self.dimension_rows),
            }

            source_image_path = self.image_path_var.get()
            if source_image_path:
                printable["image_file"] = ProductService.copy_image_to_assets(
                    source_image_path, self.assets_path
                )
            product["printable"] = printable

        if product["id"] in self.catalog and product["id"] != self.editing_item_id:
            messagebox.showerror("Duplicate ID", f"The ID '{product['id']}' already exists in the catalog.")
            return

        # If editing, remove from original file first
        if self.editing_item_id:
            orig_yaml_path = os.path.join(self.categories_path, self.editing_original_cat)
            if os.path.exists(orig_yaml_path):
                ProductService.remove_from_yaml(
                    self.editing_item_id, self.editing_original_cat, self.categories_path
                )

        ProductService.upsert_to_yaml(product, cat_file, self.categories_path)

        messagebox.showinfo("Success", f"Product '{product['id']}' saved successfully!")
        
        self.catalog = self.db_loader.load_all_categories()
        self.master.catalog = self.catalog
        if hasattr(self.master, 'refresh_match_service'):
            self.master.refresh_match_service()
        if hasattr(self.master, 'populate_verification_ui'):
            self.master.populate_verification_ui()
            
        self.show_browser_view()

    def show_bulk_load_ui(self):
        BulkLoadWindow(self, self.db_loader, self.categories_path, self.assets_path, self.refresh_browser_list)

class BulkLoadWindow(ctk.CTkToplevel):
    def __init__(self, master, db_loader, categories_path, assets_path, refresh_callback):
        super().__init__(master)
        
        self.title("Bulk Load Products (CSV)")
        self.geometry("700x600")
        self.transient(master)
        self.grab_set()
        self.focus_set()
        self.attributes("-topmost", True)
        
        self.categories_path = categories_path
        self.assets_path = assets_path
        self.refresh_callback = refresh_callback
        
        self.csv_path = None
        self.image_dir = None
        
        self.build_ui()
        self.after(100, lambda: self.attributes("-topmost", False))

    def build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        
        header_lbl = ctk.CTkLabel(self, text="Bulk Import Products via CSV", font=ctk.CTkFont(size=20, weight="bold"))
        header_lbl.grid(row=0, column=0, pady=(20, 10), padx=20, sticky="w")
        
        info_text = (
            "1. Generate a CSV Template below.\n"
            "2. Fill it out in Excel (each row = 1 product).\n"
            "3. Place all your new image files in a separate folder.\n"
            "4. Select the filled CSV, the image folder, and run the import."
        )
        info_lbl = ctk.CTkLabel(self, text=info_text, justify="left", font=ctk.CTkFont(size=14))
        info_lbl.grid(row=1, column=0, pady=(0, 20), padx=20, sticky="w")
        
        btn_template = ctk.CTkButton(self, text="⬇️ Generate CSV Template", command=self.generate_template, fg_color="green", hover_color="darkgreen")
        btn_template.grid(row=2, column=0, pady=(0, 30), padx=20, sticky="w")
        
        # File Selectors
        sel_frame = ctk.CTkFrame(self)
        sel_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=10)
        sel_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkButton(sel_frame, text="1. Select Filled CSV", command=self.select_csv).grid(row=0, column=0, padx=10, pady=10)
        self.lbl_csv = ctk.CTkLabel(sel_frame, text="No file selected...", text_color="gray")
        self.lbl_csv.grid(row=0, column=1, sticky="w", padx=10)
        
        ctk.CTkButton(sel_frame, text="2. Select Image Folder", command=self.select_image_dir).grid(row=1, column=0, padx=10, pady=10)
        self.lbl_image_dir = ctk.CTkLabel(sel_frame, text="(Optional) Select folder containing new images...", text_color="gray")
        self.lbl_image_dir.grid(row=1, column=1, sticky="w", padx=10)
        
        self.btn_run = ctk.CTkButton(self, text="🚀 Run Import", command=self.run_import, height=50, font=ctk.CTkFont(size=16, weight="bold"), state="disabled")
        self.btn_run.grid(row=4, column=0, pady=30, padx=20, sticky="ew")

    def generate_template(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="bulk_import_template.csv", title="Save CSV Template", filetypes=[("CSV File", "*.csv")])
        if not filepath: return
        
        headers = ["category_file", "id", "sku", "brand", "provider", "routing_tag", "purchase_link", "oneclick_description", 
                   "is_printable", "finish", "description", "dim_width", "dim_height", "dim_depth", "image_file"]
                   
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                # Write an example row
                writer.writerow(["vanities.yaml", "PKB-VAN-EXAMPLE", "SKU123", "Kohler", "Kohler Direct", "Warehouse", "", "Modern Vanity 48", 
                                 "yes", "Matte Black", "A beautiful vanity.", "48\"", "34\"", "22\"", "vanity_pic.jpg"])
            messagebox.showinfo("Success", f"Template generated successfully at:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create template: {e}")

    def select_csv(self):
        filepath = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if filepath:
            self.csv_path = filepath
            self.lbl_csv.configure(text=os.path.basename(filepath), text_color="white")
            self.check_ready()

    def select_image_dir(self):
        dirpath = filedialog.askdirectory(title="Select Folder with New Images")
        if dirpath:
            self.image_dir = dirpath
            self.lbl_image_dir.configure(text=os.path.basename(dirpath), text_color="white")

    def check_ready(self):
        if self.csv_path:
            self.btn_run.configure(state="normal")
        else:
            self.btn_run.configure(state="disabled")

    def run_import(self):
        if not self.csv_path: return
        
        success_count = 0
        error_count = 0
        errors = []
        
        # Load existing DB to check for duplicate IDs
        db_loader = self.master.db_loader
        catalog_cache = db_loader.load_all_categories()
        existing_ids = set()
        for item in catalog_cache.values():
            existing_ids.add(str(item.get('id', '')))

        try:
            with open(self.csv_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                # Normalize keys
                reader.fieldnames = [k.strip() for k in reader.fieldnames]
                
                required_cols = ["category_file", "id", "sku", "oneclick_description"]
                for col in required_cols:
                    if col not in reader.fieldnames:
                        messagebox.showerror("Error", f"CSV is missing required column: {col}. Generated template has exact column names.")
                        return

                for row_num, row in enumerate(reader, start=2):
                    cat_file = row.get("category_file", "").strip()
                    item_id = row.get("id", "").strip()
                    
                    if not item_id or not cat_file:
                        continue # Skip empty rows
                        
                    if not cat_file.endswith(".yaml"):
                        cat_file += ".yaml"
                        
                    if str(item_id) in existing_ids:
                        errors.append(f"Row {row_num}: Duplicate ID '{item_id}'")
                        error_count += 1
                        continue
                        
                    product = {
                        "id": item_id,
                        "sku": row.get("sku", "").strip(),
                        "brand": row.get("brand", "").strip(),
                        "provider": row.get("provider", "").strip(),
                        "routing_tag": row.get("routing_tag", "").strip(),
                        "purchase_link": row.get("purchase_link", "").strip(),
                        "oneclick_description": row.get("oneclick_description", "").strip(),
                    }
                    
                    is_printable = str(row.get("is_printable", "")).strip().lower() in ['yes', 'y', '1', 'true']
                    
                    if is_printable:
                        printable = {
                            "finish": row.get("finish", "").strip(),
                            "description": row.get("description", "").strip(),
                            "dimensions": {}
                        }
                        
                        if row.get("dim_width", "").strip(): printable["dimensions"]["width"] = row.get("dim_width", "").strip()
                        if row.get("dim_height", "").strip(): printable["dimensions"]["height"] = row.get("dim_height", "").strip()
                        if row.get("dim_depth", "").strip(): printable["dimensions"]["depth"] = row.get("dim_depth", "").strip()
                        
                        img_name = row.get("image_file", "").strip()
                        if img_name:
                            printable["image_file"] = img_name
                            
                            # Try to copy it over if image dir provided
                            if self.image_dir:
                                source_path = os.path.join(self.image_dir, img_name)
                                dest_path = os.path.join(self.assets_path, img_name)
                                if os.path.exists(source_path) and os.path.abspath(source_path) != os.path.abspath(dest_path):
                                    try:
                                        shutil.copy(source_path, dest_path)
                                    except Exception as copy_e:
                                        errors.append(f"Row {row_num}: Failed to copy image {img_name}: {copy_e}")
                                else:
                                    if not os.path.exists(dest_path) and not os.path.exists(source_path):
                                        errors.append(f"Row {row_num}: Image {img_name} not found in source dir.")
                                        
                        product["printable"] = printable
                    
                    # Append to YAML
                    target_yaml_path = os.path.join(self.categories_path, cat_file)
                    existing_data = []
                    if os.path.exists(target_yaml_path):
                        with open(target_yaml_path, 'r', encoding='utf-8') as yf:
                            existing_data = yaml.safe_load(yf) or []
                            
                    existing_data.append(product)
                    
                    with open(target_yaml_path, 'w', encoding='utf-8') as yf:
                        yaml.dump(existing_data, yf, sort_keys=False, allow_unicode=True)
                        
                    existing_ids.add(str(item_id)) # Add to cache
                    success_count += 1
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read CSV: {e}")
            return
            
        self.refresh_callback()
        
        msg = f"Import Finished!\nSuccessfully imported: {success_count} items.\nFailed: {error_count} items."
        if errors:
            msg += "\n\nFirst 5 Warnings/Errors:\n" + "\n".join(errors[:5])
            
        messagebox.showinfo("Import Complete", msg)
        self.destroy()
