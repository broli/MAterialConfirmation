import customtkinter as ctk
import tkinter.messagebox as messagebox
from tkinter import filedialog
import os
import yaml
import shutil
from PIL import Image

# Import our backend engine
from catalog_loader import CatalogLoader
from session_manager import SessionManager
from pdf_engine import PDFGenerator

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class PKBApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("PKB Material Confirmation System")
        self.geometry("1000x700")

        # Load Database
        self.db_loader = CatalogLoader()
        self.catalog = self.db_loader.load_all_categories()
        self.selected_items = []
        
        # State variables for editing
        self.editing_item_id = None
        self.editing_original_cat = None

        # --- Main Layout: Tabs ---
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tab_gen = self.tabview.add("Document Generator")
        self.tab_admin = self.tabview.add("Catalog Manager")

        self.setup_generator_tab()
        self.setup_admin_tab()

    # ==========================================
    # TAB 1: DOCUMENT GENERATOR
    # ==========================================
    def setup_generator_tab(self):
        self.tab_gen.grid_columnconfigure(1, weight=1)
        self.tab_gen.grid_rowconfigure(0, weight=1)

        # 1. Left Sidebar (Client Info)
        self.sidebar_frame = ctk.CTkFrame(self.tab_gen, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="PKB Systems", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.client_name_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Client Name")
        self.client_name_entry.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.project_name_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Project / Address")
        self.project_name_entry.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.generate_btn = ctk.CTkButton(self.sidebar_frame, text="Generate PDF", command=self.generate_pdf, fg_color="green", hover_color="darkgreen")
        self.generate_btn.grid(row=5, column=0, padx=20, pady=20, sticky="ew")

        # 2. Middle Panel (Search & Catalog Picker)
        self.middle_frame = ctk.CTkFrame(self.tab_gen, fg_color="transparent")
        self.middle_frame.grid(row=0, column=1, padx=(20, 10), pady=20, sticky="nsew")
        self.middle_frame.grid_columnconfigure(0, weight=1)
        self.middle_frame.grid_rowconfigure(1, weight=1)

        self.search_entry = ctk.CTkEntry(self.middle_frame, placeholder_text="Search by Brand, Model, Type, Finish, or ID...")
        self.search_entry.grid(row=0, column=0, pady=(0, 10), sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.on_search)

        self.catalog_frame = ctk.CTkScrollableFrame(self.middle_frame, label_text="Master Catalog")
        self.catalog_frame.grid(row=1, column=0, sticky="nsew")
        self.populate_catalog_list()

        # 3. Right Panel (Current Selection)
        self.selection_frame = ctk.CTkScrollableFrame(self.tab_gen, label_text="Client Selection", width=250)
        self.selection_frame.grid(row=0, column=2, padx=(10, 20), pady=20, sticky="nsew")

    def on_search(self, event):
        query = self.search_entry.get().strip().lower()
        self.populate_catalog_list(query)

    def populate_catalog_list(self, query=""):
        for widget in self.catalog_frame.winfo_children():
            widget.destroy()

        if not self.catalog:
            ctk.CTkLabel(self.catalog_frame, text="No products found.", text_color="red").pack(pady=20)
            return

        grouped_items = {}
        for item_id, item in self.catalog.items():
            if query:
                search_text = f"{item.get('brand','')} {item.get('model','')} {item.get('finish','')} {item.get('type','')} {item_id}".lower()
                if query not in search_text:
                    continue
            
            cat = item.get('category_file', 'Uncategorized').replace('_', ' ').title()
            if cat not in grouped_items:
                grouped_items[cat] = []
            grouped_items[cat].append((item_id, item))

        if not grouped_items:
            ctk.CTkLabel(self.catalog_frame, text="No matches found.").pack(pady=20)
            return

        for cat in sorted(grouped_items.keys()):
            cat_lbl = ctk.CTkLabel(self.catalog_frame, text=cat.upper(), font=ctk.CTkFont(weight="bold", size=14), text_color="#00BFFF")
            cat_lbl.pack(anchor="w", pady=(15, 2), padx=5)

            for item_id, item_data in grouped_items[cat]:
                # FIX: Injected Finish into the button string for clarity
                finish = item_data.get('finish', '')
                finish_str = f" - {finish}" if finish else ""
                
                btn_text = f"{item_data.get('brand')} {item_data.get('model')}{finish_str} ({item_data.get('type')})"
                btn = ctk.CTkButton(self.catalog_frame, text=btn_text, anchor="w", 
                                    command=lambda idx=item_id: self.add_to_selection(idx))
                btn.pack(pady=2, padx=10, fill="x")

    def add_to_selection(self, item_id):
        if item_id not in self.selected_items:
            self.selected_items.append(item_id)
            self.refresh_selection_ui()

    def remove_from_selection(self, item_id):
        if item_id in self.selected_items:
            self.selected_items.remove(item_id)
            self.refresh_selection_ui()

    def refresh_selection_ui(self):
        for widget in self.selection_frame.winfo_children():
            widget.destroy()

        for item_id in self.selected_items:
            item_data = self.catalog.get(item_id, {})
            
            # FIX: Also added finish to the right-side selection list
            finish = item_data.get('finish', '')
            finish_str = f" - {finish}" if finish else ""
            short_name = f"{item_data.get('brand')} {item_data.get('model')}{finish_str}"
            
            frame = ctk.CTkFrame(self.selection_frame, fg_color="transparent")
            frame.pack(fill="x", pady=2)
            
            lbl = ctk.CTkLabel(frame, text=short_name, width=150, anchor="w")
            lbl.pack(side="left", padx=5)
            # Add tooltip or wrap text if it gets too long
            lbl.configure(wraplength=150)
            
            ctk.CTkButton(frame, text="X", width=30, fg_color="red", hover_color="darkred",
                          command=lambda idx=item_id: self.remove_from_selection(idx)).pack(side="right", padx=5)

    def generate_pdf(self):
        client_name = self.client_name_entry.get().strip()
        if not client_name or not self.selected_items:
            messagebox.showwarning("Missing Data", "Please enter a Client Name and select items.")
            return

        session_data = {
            "client_info": {
                "name": client_name,
                "project": self.project_name_entry.get().strip()
            },
            "selected_items": [{"id": i} for i in self.selected_items]
        }
        
        os.makedirs("sessions", exist_ok=True)
        session_filename = f"gui_session_{client_name.replace(' ', '_')}.yaml"
        
        with open(os.path.join("sessions", session_filename), 'w', encoding='utf-8') as f:
            yaml.dump(session_data, f, sort_keys=False)

        try:
            session_mgr = SessionManager(self.db_loader)
            pdf_payload = session_mgr.process_client_session(session_filename)
            if pdf_payload:
                pdf_maker = PDFGenerator()
                output_file = pdf_maker.create_pdf(pdf_payload)
                messagebox.showinfo("Success", f"PDF Generated!\nSaved to: {output_file}")
        except Exception as e:
            messagebox.showerror("Critical Error", f"Failed to generate:\n{e}")

    # ==========================================
    # TAB 2: CATALOG MANAGER (ADMIN)
    # ==========================================
    def setup_admin_tab(self):
        self.tab_admin.grid_columnconfigure(0, weight=1)
        self.tab_admin.grid_rowconfigure(0, weight=1)

        self.admin_container = ctk.CTkFrame(self.tab_admin, fg_color="transparent")
        self.admin_container.grid(row=0, column=0, sticky="nsew")
        self.admin_container.grid_columnconfigure(0, weight=1)
        self.admin_container.grid_rowconfigure(0, weight=1) 

        self.build_browser_view()
        self.build_form_view()
        self.show_browser_view()

    def get_unique_values(self, key):
        values = set()
        for item in self.catalog.values():
            if key in item and item[key]:
                values.add(item[key])
        return sorted(list(values))

    def get_existing_categories(self):
        cat_path = os.path.join("database", "categories")
        if not os.path.exists(cat_path):
            return ["faucets.yaml", "vanities.yaml"] 
        return [f for f in os.listdir(cat_path) if f.endswith('.yaml')]

    # --- View 1: Database Browser ---
    def build_browser_view(self):
        self.browser_frame = ctk.CTkFrame(self.admin_container, fg_color="transparent")
        self.browser_frame.grid_columnconfigure(0, weight=1)
        self.browser_frame.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.browser_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(header, text="Database Browser (Click item to view/edit/delete)", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="+ Add New Product", command=self.show_form_view, fg_color="green", hover_color="darkgreen").pack(side="right")

        self.tree_frame = ctk.CTkScrollableFrame(self.browser_frame)
        self.tree_frame.grid(row=1, column=0, sticky="nsew")

    def refresh_browser_list(self):
        for widget in self.tree_frame.winfo_children():
            widget.destroy()

        cat_path = os.path.join("database", "categories")
        if not os.path.exists(cat_path):
            return

        txt_color = ctk.ThemeManager.theme["CTkLabel"]["text_color"]

        for cat_file in os.listdir(cat_path):
            if not cat_file.endswith('.yaml'): continue
            
            cat_header = ctk.CTkLabel(self.tree_frame, text=f"📁 {cat_file.upper()}", font=ctk.CTkFont(weight="bold", size=14), text_color="#00BFFF")
            cat_header.pack(anchor="w", pady=(15, 2), padx=5)
            
            file_path = os.path.join(cat_path, cat_file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    items = yaml.safe_load(f) or []
                    for item in items:
                        text = f"  ├─ [{item.get('id')}] : {item.get('brand')} {item.get('model')} - {item.get('finish')}"
                        
                        btn = ctk.CTkButton(self.tree_frame, text=text, font=ctk.CTkFont(family="Courier", size=12),
                                            fg_color="transparent", text_color=txt_color,
                                            hover_color=("gray70", "gray30"), anchor="w",
                                            command=lambda idx=item.get('id'): self.view_product_details(idx))
                        btn.pack(anchor="w", padx=10, fill="x")
            except Exception:
                pass

    # --- View 1.5: Product Details / Edit / Delete Pop-up ---
    def view_product_details(self, item_id):
        item = self.catalog.get(item_id)
        if not item: return

        top = ctk.CTkToplevel(self)
        top.title(f"Product Details - {item_id}")
        top.geometry("500x680")
        top.attributes("-topmost", True)

        # Image Display
        img_file = item.get("image_file")
        if img_file:
            img_path = os.path.join("database", "assets", img_file)
            if os.path.exists(img_path):
                try:
                    pil_img = Image.open(img_path)
                    pil_img.thumbnail((300, 300))
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                    lbl_img = ctk.CTkLabel(top, image=ctk_img, text="")
                    lbl_img.pack(pady=15)
                except Exception as e:
                    ctk.CTkLabel(top, text=f"[ Image Error: {e} ]", text_color="red").pack(pady=10)
        
        # Details Text
        details = f"ID: {item_id}\n"
        details += f"Category File: {item.get('category_file', 'N/A')}.yaml\n\n"
        details += f"Brand: {item.get('brand')}\n"
        details += f"Model: {item.get('model')}\n"
        details += f"Type: {item.get('type')}\n"
        details += f"Finish: {item.get('finish')}\n"
        
        dims = item.get("dimensions", {})
        if dims:
            dim_str = ", ".join([f"{k}: {v}" for k, v in dims.items()])
            details += f"Dimensions: {dim_str}\n"

        lbl_details = ctk.CTkLabel(top, text=details, justify="left", font=ctk.CTkFont(size=14))
        lbl_details.pack(pady=5, padx=20, anchor="w")

        desc = ctk.CTkTextbox(top, height=80, width=460)
        desc.insert("0.0", item.get("description", ""))
        desc.configure(state="disabled")
        desc.pack(pady=10, padx=20)

        # Action Buttons Frame
        btn_frame = ctk.CTkFrame(top, fg_color="transparent")
        btn_frame.pack(side="bottom", pady=20, fill="x", padx=20)

        btn_edit = ctk.CTkButton(btn_frame, text="Edit Product", fg_color="#153E83", hover_color="#0d2b61",
                                 command=lambda: self.load_for_edit(item_id, top))
        btn_edit.pack(side="left", expand=True, padx=10)

        btn_delete = ctk.CTkButton(btn_frame, text="Delete Product", fg_color="red", hover_color="darkred",
                                   command=lambda: self.delete_product(item_id, top))
        btn_delete.pack(side="right", expand=True, padx=10)

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
        self.brand_combobox.set(item.get('brand', ''))
        self.model_entry.insert(0, item.get('model', ''))
        self.type_combobox.set(item.get('type', ''))
        self.finish_combobox.set(item.get('finish', ''))
        
        dims = item.get('dimensions', {})
        self.w_entry.insert(0, dims.get('width', ''))
        self.h_entry.insert(0, dims.get('height', ''))
        self.d_entry.insert(0, dims.get('depth', ''))

        self.desc_entry.delete("0.0", "end")
        self.desc_entry.insert("0.0", item.get('description', ''))

        if item.get('image_file'):
            abs_img_path = os.path.abspath(os.path.join("database", "assets", item.get('image_file')))
            if os.path.exists(abs_img_path):
                self.image_path_var.set(abs_img_path)

    def delete_product(self, item_id, window=None):
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to permanently delete ID: {item_id}?")
        if not confirm: return

        item = self.catalog.get(item_id)
        cat_file = item.get('category_file') + '.yaml'
        target_yaml_path = os.path.join("database", "categories", cat_file)

        if os.path.exists(target_yaml_path):
            with open(target_yaml_path, 'r', encoding='utf-8') as f:
                existing_data = yaml.safe_load(f) or []

            new_data = [i for i in existing_data if i.get('id') != item_id]

            with open(target_yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(new_data, f, sort_keys=False, allow_unicode=True)

        self.catalog = self.db_loader.load_all_categories()
        self.populate_catalog_list() 
        self.refresh_browser_list()  

        if window:
            window.destroy()
        messagebox.showinfo("Deleted", f"Product {item_id} has been removed.")

    # --- View 2: Add / Edit Product Form ---
    def build_form_view(self):
        self.form_frame = ctk.CTkFrame(self.admin_container, fg_color="transparent")
        self.form_frame.grid_columnconfigure((0, 1), weight=1)

        header = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        ctk.CTkButton(header, text="← Back", command=self.show_browser_view, width=60).pack(side="left")
        
        self.form_header_label = ctk.CTkLabel(header, text="Add New Product", font=ctk.CTkFont(size=18, weight="bold"))
        self.form_header_label.pack(side="left", padx=20)

        # Basic Info with Smart Comboboxes & Labels
        ctk.CTkLabel(self.form_frame, text="Category File", anchor="w").grid(row=1, column=0, padx=10, pady=(10, 0), sticky="ew")
        ctk.CTkLabel(self.form_frame, text="Unique ID", anchor="w").grid(row=1, column=1, padx=10, pady=(10, 0), sticky="ew")
        
        self.cat_combobox = ctk.CTkComboBox(self.form_frame, values=self.get_existing_categories())
        self.cat_combobox.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")

        self.id_entry = ctk.CTkEntry(self.form_frame)
        self.id_entry.grid(row=2, column=1, padx=10, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(self.form_frame, text="Brand", anchor="w").grid(row=3, column=0, padx=10, pady=(10, 0), sticky="ew")
        ctk.CTkLabel(self.form_frame, text="Model", anchor="w").grid(row=3, column=1, padx=10, pady=(10, 0), sticky="ew")

        self.brand_combobox = ctk.CTkComboBox(self.form_frame, values=self.get_unique_values('brand'))
        self.brand_combobox.grid(row=4, column=0, padx=10, pady=(0, 10), sticky="ew")

        self.model_entry = ctk.CTkEntry(self.form_frame)
        self.model_entry.grid(row=4, column=1, padx=10, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(self.form_frame, text="Type", anchor="w").grid(row=5, column=0, padx=10, pady=(10, 0), sticky="ew")
        ctk.CTkLabel(self.form_frame, text="Finish", anchor="w").grid(row=5, column=1, padx=10, pady=(10, 0), sticky="ew")

        self.type_combobox = ctk.CTkComboBox(self.form_frame, values=self.get_unique_values('type'))
        self.type_combobox.grid(row=6, column=0, padx=10, pady=(0, 10), sticky="ew")

        self.finish_combobox = ctk.CTkComboBox(self.form_frame, values=self.get_unique_values('finish'))
        self.finish_combobox.grid(row=6, column=1, padx=10, pady=(0, 10), sticky="ew")

        dim_frame = ctk.CTkFrame(self.form_frame)
        dim_frame.grid(row=7, column=0, columnspan=2, pady=10, sticky="ew", padx=10)
        ctk.CTkLabel(dim_frame, text="Dimensions (Optional - use inches like 48\")").pack(side="left", padx=10)
        
        self.w_entry = ctk.CTkEntry(dim_frame, placeholder_text="Width", width=80)
        self.w_entry.pack(side="left", padx=5)
        self.h_entry = ctk.CTkEntry(dim_frame, placeholder_text="Height", width=80)
        self.h_entry.pack(side="left", padx=5)
        self.d_entry = ctk.CTkEntry(dim_frame, placeholder_text="Depth", width=80)
        self.d_entry.pack(side="left", padx=5)

        ctk.CTkLabel(self.form_frame, text="Marketing Description", anchor="w").grid(row=8, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="ew")
        
        self.desc_entry = ctk.CTkTextbox(self.form_frame, height=60)
        self.desc_entry.grid(row=9, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")

        self.image_path_var = ctk.StringVar(value="")
        img_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        img_frame.grid(row=10, column=0, columnspan=2, pady=10, sticky="ew", padx=10)
        
        ctk.CTkButton(img_frame, text="Browse Image...", command=self.browse_image).pack(side="left", padx=10)
        ctk.CTkLabel(img_frame, textvariable=self.image_path_var).pack(side="left")

        ctk.CTkButton(self.form_frame, text="Save to Database", command=self.save_product, fg_color="blue", height=40).grid(row=11, column=0, columnspan=2, pady=20)

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
        self.type_combobox.configure(values=self.get_unique_values('type'))
        self.finish_combobox.configure(values=self.get_unique_values('finish'))
        self.cat_combobox.configure(values=self.get_existing_categories())

        if self.get_existing_categories():
            self.cat_combobox.set(self.get_existing_categories()[0]) 
            
        self.id_entry.delete(0, 'end')
        self.model_entry.delete(0, 'end')
        self.w_entry.delete(0, 'end')
        self.h_entry.delete(0, 'end')
        self.d_entry.delete(0, 'end')
        self.desc_entry.delete("0.0", "end")
        self.image_path_var.set("")

    # --- Form Actions ---
    def browse_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.jpeg *.png")])
        if file_path:
            self.image_path_var.set(file_path)

    def save_product(self):
        cat_file = self.cat_combobox.get().strip()
        if not cat_file.endswith(".yaml"):
            cat_file += ".yaml"

        product = {
            "id": self.id_entry.get().strip(),
            "brand": self.brand_combobox.get().strip(),
            "model": self.model_entry.get().strip(),
            "type": self.type_combobox.get().strip(),
            "finish": self.finish_combobox.get().strip(),
            "description": self.desc_entry.get("0.0", "end").strip(),
            "dimensions": {}
        }

        if self.w_entry.get().strip(): product["dimensions"]["width"] = self.w_entry.get().strip()
        if self.h_entry.get().strip(): product["dimensions"]["height"] = self.h_entry.get().strip()
        if self.d_entry.get().strip(): product["dimensions"]["depth"] = self.d_entry.get().strip()

        if not product["id"] or not product["brand"]:
            messagebox.showwarning("Incomplete Data", "ID and Brand are required.")
            return

        if product["id"] in self.catalog and product["id"] != self.editing_item_id:
            messagebox.showerror("Duplicate ID", f"The ID '{product['id']}' already exists in the catalog.")
            return

        source_image_path = self.image_path_var.get()
        if source_image_path:
            filename = os.path.basename(source_image_path)
            dest_image_path = os.path.join("database", "assets", filename)
            
            if os.path.abspath(source_image_path) != os.path.abspath(dest_image_path):
                shutil.copy(source_image_path, dest_image_path)
            product["image_file"] = filename
        else:
            messagebox.showwarning("Missing Image", "Please select a product image.")
            return

        target_yaml_path = os.path.join("database", "categories", cat_file)

        if self.editing_item_id:
            orig_yaml_path = os.path.join("database", "categories", self.editing_original_cat)
            if os.path.exists(orig_yaml_path):
                with open(orig_yaml_path, 'r', encoding='utf-8') as f:
                    old_data = yaml.safe_load(f) or []
                
                old_data = [i for i in old_data if i.get('id') != self.editing_item_id]
                
                with open(orig_yaml_path, 'w', encoding='utf-8') as f:
                    yaml.dump(old_data, f, sort_keys=False, allow_unicode=True)

        existing_data = []
        if os.path.exists(target_yaml_path):
            with open(target_yaml_path, 'r', encoding='utf-8') as f:
                existing_data = yaml.safe_load(f) or []
        
        existing_data = [i for i in existing_data if i.get('id') != product["id"]]
        existing_data.append(product)

        with open(target_yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(existing_data, f, sort_keys=False, allow_unicode=True)

        messagebox.showinfo("Success", f"Product '{product['id']}' saved successfully!")
        
        self.catalog = self.db_loader.load_all_categories()
        self.search_entry.delete(0, 'end')
        self.populate_catalog_list()
        
        self.show_browser_view()

# --- Execution ---
if __name__ == "__main__":
    app = PKBApp()
    app.mainloop()