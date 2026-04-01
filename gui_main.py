import customtkinter as ctk
import tkinter.messagebox as messagebox
import os
import yaml
from datetime import datetime

# Import our backend engine
from catalog_loader import CatalogLoader
from session_manager import SessionManager
from pdf_engine import PDFGenerator

# Set the appearance and color theme
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class PKBApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("PKB Material Confirmation Generator")
        self.geometry("900x600")

        # Load Database
        self.db_loader = CatalogLoader()
        self.catalog = self.db_loader.load_all_categories()
        
        # State variables
        self.selected_items = []

        # --- UI Layout ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. Left Sidebar (Client Info)
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="PKB Systems", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.client_name_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Client Name")
        self.client_name_entry.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.project_name_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Project / Address")
        self.project_name_entry.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.date_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Date (YYYY-MM-DD)")
        self.date_entry.insert(0, datetime.today().strftime('%Y-%m-%d'))
        self.date_entry.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        self.generate_btn = ctk.CTkButton(self.sidebar_frame, text="Generate PDF", command=self.generate_pdf, fg_color="green", hover_color="darkgreen")
        self.generate_btn.grid(row=6, column=0, padx=20, pady=20, sticky="ew")

        # 2. Middle Panel (Catalog Picker)
        self.catalog_frame = ctk.CTkScrollableFrame(self, label_text="Master Catalog")
        self.catalog_frame.grid(row=0, column=1, padx=(20, 10), pady=20, sticky="nsew")

        self.populate_catalog_list()

        # 3. Right Panel (Current Selection)
        self.selection_frame = ctk.CTkScrollableFrame(self, label_text="Client Selection", width=250)
        self.selection_frame.grid(row=0, column=2, padx=(10, 20), pady=20, sticky="nsew")

    def populate_catalog_list(self):
        """Creates a button for every item in the loaded database."""
        if not self.catalog:
            error_lbl = ctk.CTkLabel(self.catalog_frame, text="No products found in database.", text_color="red")
            error_lbl.pack(pady=20)
            return

        for item_id, item_data in self.catalog.items():
            btn_text = f"{item_data.get('brand')} {item_data.get('model')} ({item_data.get('type')})"
            btn = ctk.CTkButton(self.catalog_frame, text=btn_text, anchor="w", 
                                command=lambda idx=item_id: self.add_to_selection(idx))
            btn.pack(pady=5, padx=10, fill="x")

    def add_to_selection(self, item_id):
        """Adds an item to the client's current session list."""
        if item_id not in self.selected_items:
            self.selected_items.append(item_id)
            self.refresh_selection_ui()

    def remove_from_selection(self, item_id):
        """Removes an item from the client's current session list."""
        if item_id in self.selected_items:
            self.selected_items.remove(item_id)
            self.refresh_selection_ui()

    def refresh_selection_ui(self):
        """Clears and redraws the right panel based on selected items."""
        for widget in self.selection_frame.winfo_children():
            widget.destroy()

        for item_id in self.selected_items:
            item_data = self.catalog.get(item_id, {})
            short_name = f"{item_data.get('brand')} {item_data.get('model')}"
            
            frame = ctk.CTkFrame(self.selection_frame, fg_color="transparent")
            frame.pack(fill="x", pady=2)
            
            lbl = ctk.CTkLabel(frame, text=short_name, width=150, anchor="w")
            lbl.pack(side="left", padx=5)
            
            del_btn = ctk.CTkButton(frame, text="X", width=30, fg_color="red", hover_color="darkred",
                                    command=lambda idx=item_id: self.remove_from_selection(idx))
            del_btn.pack(side="right", padx=5)

    def generate_pdf(self):
        """Compiles the data, saves a session YAML, and triggers the PDF engine."""
        client_name = self.client_name_entry.get().strip()
        
        if not client_name:
            messagebox.showwarning("Missing Data", "Please enter a Client Name.")
            return
        if not self.selected_items:
            messagebox.showwarning("Missing Data", "Please select at least one product.")
            return

        # 1. Create a temporary session YAML file for this GUI state
        session_data = {
            "client_info": {
                "name": client_name,
                "project": self.project_name_entry.get().strip(),
                "date": self.date_entry.get().strip()
            },
            "selected_items": [{"id": item_id} for item_id in self.selected_items]
        }
        
        os.makedirs("sessions", exist_ok=True)
        session_filename = f"gui_session_{client_name.replace(' ', '_')}.yaml"
        session_path = os.path.join("sessions", session_filename)
        
        try:
            with open(session_path, 'w', encoding='utf-8') as f:
                yaml.dump(session_data, f, sort_keys=False)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save session file:\n{e}")
            return

        # 2. Run the Backend Process
        try:
            session_mgr = SessionManager(self.db_loader)
            pdf_payload = session_mgr.process_client_session(session_filename)
            
            if pdf_payload:
                pdf_maker = PDFGenerator()
                output_file = pdf_maker.create_pdf(pdf_payload)
                messagebox.showinfo("Success", f"PDF Generated Successfully!\nSaved to: {output_file}")
            else:
                messagebox.showerror("Error", "Failed to process payload for PDF.")
        except Exception as e:
            messagebox.showerror("Critical Error", f"An error occurred during generation:\n{e}")

# --- Execution ---
if __name__ == "__main__":
    app = PKBApp()
    app.mainloop()