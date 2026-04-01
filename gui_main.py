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
        self.tab_admin.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(self.tab_admin, text="Add New Product to Database", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)

        # Basic Info
        self.cat_entry = ctk.CTkEntry(self.tab_admin, placeholder_text="Category File (e.g., faucets.yaml)")
        self.cat_entry.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.id_entry = ctk.CTkEntry(self.tab_admin, placeholder_text="Unique ID (e.g., KHL_PUR_02)")
        self.id_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        self.brand_entry = ctk.CTkEntry(self.tab_admin, placeholder_text="Brand (e.g., Kohler)")
        self.brand_entry.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.model_entry = ctk.CTkEntry(self.tab_admin, placeholder_text="Model (e.g., Purist)")
        self.model_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        self.type_entry = ctk.CTkEntry(self.tab_admin, placeholder_text="Type (e.g., Widespread Faucet)")
        self.type_entry.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        self.finish_entry = ctk.CTkEntry(self.tab_admin, placeholder_text="Finish (e.g., Matte Black)")
        self.finish_entry.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

        # Dimensions
        dim_frame = ctk.CTkFrame(self.tab_admin)
        dim_frame.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew", padx=10)
        ctk.CTkLabel(dim_frame, text="Dimensions (Optional - use inches like 48\")").pack(side="left", padx=10)
        
        self.w_entry = ctk.CTkEntry(dim_frame, placeholder_text="Width", width=80)
        self.w_entry.pack(side="left", padx=5)
        self.h_entry = ctk.CTkEntry(dim_frame, placeholder_text="Height", width=80)
        self.h_entry.pack(side="left", padx=5)
        self.d_entry = ctk.CTkEntry(dim_frame, placeholder_text="Depth", width=80)
        self.d_entry.pack(side="left", padx=5)

        # Description
        self.desc_entry = ctk.CTkTextbox(self.tab_admin, height=60)
        self.desc_entry.insert("0.0", "Marketing description here...")
        self.desc_entry.grid(row=5, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # Image Upload
        self.image_path_var = ctk.StringVar(value="")
        img_frame = ctk.CTkFrame(self.tab_admin, fg_color="transparent")
        img_frame.grid(row=6, column=0, columnspan=2, pady=10, sticky="ew", padx=10)
        
        ctk.CTkButton(img_frame, text="Browse Image...", command=self.browse_image).pack(side="left", padx=10)
        ctk.CTkLabel(img_frame, textvariable=self.image_path_var).pack(side="left")

        # Save Button
        ctk.CTkButton(self.tab_admin, text="Save to Database", command=self.save_product, fg_color="blue", height=40).grid(row=7, column=0, columnspan=2, pady=20)

    def browse_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.jpeg *.png")])
        if file_path:
            self.image_path_var.set(file_path)

    def save_product(self):
        cat_file = self.cat_entry.get().strip()
        if not cat_file.endswith(".yaml"):
            cat_file += ".yaml"

        # Construct the product dictionary
        product = {
            "id": self.id_entry.get().strip(),
            "brand": self.brand_entry.get().strip(),
            "model": self.model_entry.get().strip(),
            "type": self.type_entry.get().strip(),
            "finish": self.finish_entry.get().strip(),
            "description": self.desc_entry.get("0.0", "end").strip(),
            "dimensions": {}
        }

        # Add optional dimensions
        if self.w_entry.get().strip(): product["dimensions"]["width"] = self.w_entry.get().strip()
        if self.h_entry.get().strip(): product["dimensions"]["height"] = self.h_entry.get().strip()
        if self.d_entry.get().strip(): product["dimensions"]["depth"] = self.d_entry.get().strip()

        # Basic Validation
        if not product["id"] or not product["brand"]:
            messagebox.showwarning("Incomplete Data", "ID and Brand are required.")
            return

        # Handle Image Copying
        source_image_path = self.image_path_var.get()
        if source_image_path:
            filename = os.path.basename(source_image_path)
            dest_image_path = os.path.join("database", "assets", filename)
            
            # Only copy if the file isn't already in the assets folder
            if os.path.abspath(source_image_path) != os.path.abspath(dest_image_path):
                shutil.copy(source_image_path, dest_image_path)
            
            product["image_file"] = filename
        else:
            messagebox.showwarning("Missing Image", "Please select a product image.")
            return

        # Append to YAML
        target_yaml_path = os.path.join("database", "categories", cat_file)
        
        # Load existing data to append correctly
        existing_data = []
        if os.path.exists(target_yaml_path):
            with open(target_yaml_path, 'r', encoding='utf-8') as f:
                existing_data = yaml.safe_load(f) or []

        # Check for duplicate ID
        if any(item.get('id') == product["id"] for item in existing_data):
            messagebox.showerror("Duplicate ID", f"The ID '{product['id']}' already exists in {cat_file}.")
            return

        existing_data.append(product)

        with open(target_yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(existing_data, f, sort_keys=False, allow_unicode=True)

        messagebox.showinfo("Success", f"Product '{product['id']}' saved to {cat_file}!")
        
        # Reload the app's memory so the new item shows up in Tab 1 immediately
        self.catalog = self.db_loader.load_all_categories()
        self.populate_catalog_list()

# --- Execution ---
if __name__ == "__main__":
    app = PKBApp()
    app.mainloop()