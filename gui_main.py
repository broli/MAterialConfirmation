import customtkinter as ctk
import tkinter.messagebox as messagebox
from tkinter import filedialog
import os
import yaml
import shutil

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

        # 2. Middle Panel (Catalog Picker)
        self.catalog_frame = ctk.CTkScrollableFrame(self.tab_gen, label_text="Master Catalog")
        self.catalog_frame.grid(row=0, column=1, padx=(20, 10), pady=20, sticky="nsew")
        self.populate_catalog_list()

        # 3. Right Panel (Current Selection)
        self.selection_frame = ctk.CTkScrollableFrame(self.tab_gen, label_text="Client Selection", width=250)
        self.selection_frame.grid(row=0, column=2, padx=(10, 20), pady=20, sticky="nsew")

    def populate_catalog_list(self):
        for widget in self.catalog_frame.winfo_children():
            widget.destroy()

        if not self.catalog:
            ctk.CTkLabel(self.catalog_frame, text="No products found.", text_color="red").pack(pady=20)
            return

        for item_id, item_data in self.catalog.items():
            btn_text = f"{item_data.get('brand')} {item_data.get('model')} ({item_data.get('type')})"
            btn = ctk.CTkButton(self.catalog_frame, text=btn_text, anchor="w", 
                                command=lambda idx=item_id: self.add_to_selection(idx))
            btn.pack(pady=5, padx=10, fill="x")

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
            short_name = f"{item_data.get('brand')} {item_data.get('model')}"
            
            frame = ctk.CTkFrame(self.selection_frame, fg_color="transparent")
            frame.pack(fill="x", pady=2)
            
            ctk.CTkLabel(frame, text=short_name, width=150, anchor="w").pack(side="left", padx=5)
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

        # Base container for switching between Browser and Form
        self.admin_container = ctk.CTkFrame(self.tab_admin, fg_color="transparent")
        self.admin_container.grid(row=0, column=0, sticky="nsew")
        self.admin_container.grid_columnconfigure(0, weight=1)
        self.admin_container.grid_rowconfigure(1, weight=1)

        self.build_browser_view()
        self.build_form_view()

        # Start by showing the database browser
        self.show_browser_view()

    # --- Helper Data Functions ---
    def get_unique_values(self, key):
        """Scans loaded catalog for unique values to populate dropdowns."""
        values = set()
        for item in self.catalog.values():
            if key in item and item[key]:
                values.add(item[key])
        return sorted(list(values))

    def get_existing_categories(self):
        """Reads the files in the categories folder."""
        cat_path = os.path.join("database", "categories")
        if not os.path.exists(cat_path):
            return ["faucets.yaml", "vanities.yaml"] # Defaults if empty
        return [f for f in os.listdir(cat_path) if f.endswith('.yaml')]

    # --- View 1: Database Browser ---
    def build_browser_view(self):
        self.browser_frame = ctk.CTkFrame(self.admin_container, fg_color="transparent")
        self.browser_frame.grid_columnconfigure(0, weight=1)
        self.browser_frame.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self.browser_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(header, text="Database Browser", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="+ Add New Product", command=self.show_form_view, fg_color="green", hover_color="darkgreen").pack(side="right")

        # Tree/List View inside a scrollable frame
        self.tree_frame = ctk.CTkScrollableFrame(self.browser_frame)
        self.tree_frame.grid(row=1, column=0, sticky="nsew")

    def refresh_browser_list(self):
        """Draws the current YAML files and their contents."""
        for widget in self.tree_frame.winfo_children():
            widget.destroy()

        cat_path = os.path.join("database", "categories")
        if not os.path.exists(cat_path):
            return

        for cat_file in os.listdir(cat_path):
            if not cat_file.endswith('.yaml'): continue
            
            # File / Category Title
            cat_header = ctk.CTkLabel(self.tree_frame, text=f"📁 {cat_file.upper()}", font=ctk.CTkFont(weight="bold", size=14), text_color="#00BFFF")
            cat_header.pack(anchor="w", pady=(15, 2), padx=5)
            
            file_path = os.path.join(cat_path, cat_file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    items = yaml.safe_load(f) or []
                    for item in items:
                        # Product details indented
                        text = f"  ├─ [{item.get('id')}] : {item.get('brand')} {item.get('model')} - {item.get('finish')}"
                        ctk.CTkLabel(self.tree_frame, text=text, font=ctk.CTkFont(family="Courier", size=12)).pack(anchor="w", padx=10)
            except Exception:
                pass

    # --- View 2: Add Product Form ---
    def build_form_view(self):
        self.form_frame = ctk.CTkFrame(self.admin_container, fg_color="transparent")
        self.form_frame.grid_columnconfigure((0, 1), weight=1)

        # Header
        header = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        ctk.CTkButton(header, text="← Back", command=self.show_browser_view, width=60).pack(side="left")
        ctk.CTkLabel(header, text="Add New Product", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=20)

        # Basic Info with Smart Comboboxes & Labels
        # Row 1: Labels
        ctk.CTkLabel(self.form_frame, text="Category File", anchor="w").grid(row=1, column=0, padx=10, pady=(10, 0), sticky="ew")
        ctk.CTkLabel(self.form_frame, text="Unique ID", anchor="w").grid(row=1, column=1, padx=10, pady=(10, 0), sticky="ew")
        
        # Row 2: Inputs
        self.cat_combobox = ctk.CTkComboBox(self.form_frame, values=self.get_existing_categories())
        self.cat_combobox.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        if self.get_existing_categories():
            self.cat_combobox.set(self.get_existing_categories()[0]) 

        self.id_entry = ctk.CTkEntry(self.form_frame)
        self.id_entry.grid(row=2, column=1, padx=10, pady=(0, 10), sticky="ew")

        # Row 3: Labels
        ctk.CTkLabel(self.form_frame, text="Brand", anchor="w").grid(row=3, column=0, padx=10, pady=(10, 0), sticky="ew")
        ctk.CTkLabel(self.form_frame, text="Model", anchor="w").grid(row=3, column=1, padx=10, pady=(10, 0), sticky="ew")

        # Row 4: Inputs
        self.brand_combobox = ctk.CTkComboBox(self.form_frame, values=self.get_unique_values('brand'))
        self.brand_combobox.grid(row=4, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.brand_combobox.set("") 

        self.model_entry = ctk.CTkEntry(self.form_frame)
        self.model_entry.grid(row=4, column=1, padx=10, pady=(0, 10), sticky="ew")

        # Row 5: Labels
        ctk.CTkLabel(self.form_frame, text="Type", anchor="w").grid(row=5, column=0, padx=10, pady=(10, 0), sticky="ew")
        ctk.CTkLabel(self.form_frame, text="Finish", anchor="w").grid(row=5, column=1, padx=10, pady=(10, 0), sticky="ew")

        # Row 6: Inputs
        self.type_combobox = ctk.CTkComboBox(self.form_frame, values=self.get_unique_values('type'))
        self.type_combobox.grid(row=6, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.type_combobox.set("") 

        self.finish_combobox = ctk.CTkComboBox(self.form_frame, values=self.get_unique_values('finish'))
        self.finish_combobox.grid(row=6, column=1, padx=10, pady=(0, 10), sticky="ew")
        self.finish_combobox.set("") 

        # Row 7: Dimensions
        dim_frame = ctk.CTkFrame(self.form_frame)
        dim_frame.grid(row=7, column=0, columnspan=2, pady=10, sticky="ew", padx=10)
        ctk.CTkLabel(dim_frame, text="Dimensions (Optional - use inches like 48\")").pack(side="left", padx=10)
        
        self.w_entry = ctk.CTkEntry(dim_frame, placeholder_text="Width", width=80)
        self.w_entry.pack(side="left", padx=5)
        self.h_entry = ctk.CTkEntry(dim_frame, placeholder_text="Height", width=80)
        self.h_entry.pack(side="left", padx=5)
        self.d_entry = ctk.CTkEntry(dim_frame, placeholder_text="Depth", width=80)
        self.d_entry.pack(side="left", padx=5)

        # Row 8: Description Label
        ctk.CTkLabel(self.form_frame, text="Marketing Description", anchor="w").grid(row=8, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="ew")
        
        # Row 9: Description Input
        self.desc_entry = ctk.CTkTextbox(self.form_frame, height=60)
        self.desc_entry.grid(row=9, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")

        # Row 10: Image Upload
        self.image_path_var = ctk.StringVar(value="")
        img_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        img_frame.grid(row=10, column=0, columnspan=2, pady=10, sticky="ew", padx=10)
        
        ctk.CTkButton(img_frame, text="Browse Image...", command=self.browse_image).pack(side="left", padx=10)
        ctk.CTkLabel(img_frame, textvariable=self.image_path_var).pack(side="left")

        # Row 11: Save Button
        ctk.CTkButton(self.form_frame, text="Save to Database", command=self.save_product, fg_color="blue", height=40).grid(row=11, column=0, columnspan=2, pady=20)

    # --- View Switchers ---
    def show_browser_view(self):
        self.form_frame.grid_forget()
        self.browser_frame.grid(row=0, column=0, sticky="nsew")
        self.refresh_browser_list()

    def show_form_view(self):
        self.browser_frame.grid_forget()
        self.form_frame.grid(row=0, column=0, sticky="nsew")
        
        # Refresh combobox values before showing form
        self.brand_combobox.configure(values=self.get_unique_values('brand'))
        self.type_combobox.configure(values=self.get_unique_values('type'))
        self.finish_combobox.configure(values=self.get_unique_values('finish'))
        self.cat_combobox.configure(values=self.get_existing_categories())

        # Reset form fields
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
        
        existing_data = []
        if os.path.exists(target_yaml_path):
            with open(target_yaml_path, 'r', encoding='utf-8') as f:
                existing_data = yaml.safe_load(f) or []

        if any(item.get('id') == product["id"] for item in existing_data):
            messagebox.showerror("Duplicate ID", f"The ID '{product['id']}' already exists in {cat_file}.")
            return

        existing_data.append(product)

        with open(target_yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(existing_data, f, sort_keys=False, allow_unicode=True)

        messagebox.showinfo("Success", f"Product '{product['id']}' saved to {cat_file}!")
        
        self.catalog = self.db_loader.load_all_categories()
        self.populate_catalog_list()
        
        # Return to browser view after successful save
        self.show_browser_view()

# --- Execution ---
if __name__ == "__main__":
    app = PKBApp()
    app.mainloop()