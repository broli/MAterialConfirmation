import customtkinter as ctk
import tkinter.messagebox as messagebox
import os
import yaml
from PIL import Image
from catalog_loader import CatalogLoader
from database_manager import DatabaseManager

class DataFixerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Data Fixer Companion - Rapid Entry")
        self.geometry("1000x800")

        # Load Catalog
        self.db_loader = CatalogLoader()
        self.catalog = self.db_loader.load_all_categories()
        
        self.categories_path = os.path.join(self.db_loader.base_path, "categories")
        self.assets_path = os.path.join(self.db_loader.base_path, "assets")

        self.queue = []
        self.current_index = 0
        
        self.load_queue()
        self.build_ui()
        
        if not self.queue:
            messagebox.showinfo("All Done", "No items found with 'TBD_UPDATE_ME'! You are all caught up.")
            self.display_empty()
        else:
            self.display_current_item()

    def load_queue(self):
        """Scans catalog for items lacking the verified_oneclick flag"""
        self.queue = []
        for item_id, item_data in self.catalog.items():
            # If the item hasn't been explicitly verified by this tool, add it
            if not item_data.get("verified_oneclick", False):
                self.queue.append(item_data)

    def build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=10, padx=20)
        
        self.status_label = ctk.CTkLabel(self.header_frame, text="", font=ctk.CTkFont(size=20, weight="bold"))
        self.status_label.pack(side="left")
        
        self.refresh_btn = ctk.CTkButton(self.header_frame, text="↻ Refresh Queue", command=self.refresh_queue)
        self.refresh_btn.pack(side="right")

        # Main Content container
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.content_frame.grid_columnconfigure(0, weight=1) # Image column
        self.content_frame.grid_columnconfigure(1, weight=1) # Context column
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # Image Panel
        self.image_label = ctk.CTkLabel(self.content_frame, text="No Image", width=400, height=400)
        self.image_label.grid(row=0, column=0, padx=20, pady=20)

        # Context Panel
        self.context_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.context_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        self.context_text = ctk.CTkTextbox(self.context_frame, font=ctk.CTkFont(size=14))
        self.context_text.pack(expand=True, fill="both")
        self.context_text.configure(state="disabled")

        # Entry Panel
        self.entry_frame = ctk.CTkFrame(self)
        self.entry_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=20)
        self.entry_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.entry_frame, text="OneClick Description:", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=10, pady=10)
        self.oneclick_input = ctk.CTkEntry(self.entry_frame, font=ctk.CTkFont(size=16), placeholder_text="Enter exact description from agreement...")
        self.oneclick_input.grid(row=0, column=1, sticky="ew", padx=10, pady=10)
        self.oneclick_input.bind("<Return>", lambda event: self.save_and_next())

        # Buttons
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        self.btn_skip = ctk.CTkButton(self.btn_frame, text="Skip", command=self.skip, fg_color="gray")
        self.btn_skip.pack(side="left", padx=10)

        self.btn_delete = ctk.CTkButton(self.btn_frame, text="Delete Item", command=self.delete_item, fg_color="red", hover_color="darkred")
        self.btn_delete.pack(side="left", padx=10)
        
        self.btn_deep_edit = ctk.CTkButton(self.btn_frame, text="Edit Full Item", command=self.open_full_editor, fg_color="#153E83")
        self.btn_deep_edit.pack(side="left", padx=10)
        
        self.btn_save = ctk.CTkButton(self.btn_frame, text="Save & Next", command=self.save_and_next, fg_color="green", font=ctk.CTkFont(weight="bold"))
        self.btn_save.pack(side="right", padx=10)

    def refresh_queue(self):
        self.catalog = self.db_loader.load_all_categories()
        self.load_queue()
        self.current_index = 0
        if self.queue:
            self.display_current_item()
        else:
            self.display_empty()

    def display_empty(self):
        self.status_label.configure(text="Queue Empty (0 items left)")
        self.image_label.configure(image=None, text="FINISHED!")
        
        self.context_text.configure(state="normal")
        self.context_text.delete("0.0", "end")
        self.context_text.insert("0.0", "All items have been fixed.")
        self.context_text.configure(state="disabled")
        
        self.oneclick_input.delete(0, "end")
        self.oneclick_input.configure(state="disabled")
        
        self.btn_save.configure(state="disabled")
        self.btn_skip.configure(state="disabled")
        self.btn_delete.configure(state="disabled")
        self.btn_deep_edit.configure(state="disabled")

    def display_current_item(self):
        if self.current_index >= len(self.queue):
            self.display_empty()
            return
            
        self.status_label.configure(text=f"Items Remaining: {len(self.queue) - self.current_index} (Queue size: {len(self.queue)})")
        
        item = self.queue[self.current_index]
        printable = item.get('printable', {})

        # Build Context String
        ctx = f"=== SYSTEM INFO ===\n"
        ctx += f"ID: {item.get('id')}\n"
        ctx += f"SKU: {item.get('sku')}\n"
        ctx += f"Brand: {item.get('brand')}\n"
        ctx += f"Provider: {item.get('provider')}\n"
        ctx += f"Routing: {item.get('routing_tag')}\n\n"
        
        if printable:
            ctx += f"=== CLIENT PRINTABLE INFO ===\n"
            ctx += f"Finish: {printable.get('finish', 'N/A')}\n"
            dims = printable.get('dimensions', {})
            if dims:
                dim_str = ", ".join([f"{k}: {v}" for k, v in dims.items()])
                ctx += f"Dimensions: {dim_str}\n"
            ctx += f"\nDescription:\n{printable.get('description', '')}\n"
        else:
            ctx += f"=== NOT CLIENT FACING ===\n(Procurement only, no printable properties)"

        self.context_text.configure(state="normal")
        self.context_text.delete("0.0", "end")
        self.context_text.insert("0.0", ctx)
        self.context_text.configure(state="disabled")
        
        # Load Image
        image_file = printable.get('image_file')
        ctk_img = None
        if image_file:
            img_path = os.path.join(self.assets_path, image_file)
            if os.path.exists(img_path):
                try:
                    pil_img = Image.open(img_path)
                    # Resize while keeping aspect ratio constraint
                    pil_img.thumbnail((380, 380))
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                except Exception:
                    pass
                    
        if ctk_img:
            self.image_label.configure(image=ctk_img, text="")
        else:
            self.image_label.configure(image=None, text="[ No Image Found ]")

        # Reset Entry
        self.oneclick_input.configure(state="normal")
        self.oneclick_input.delete(0, "end")
        
        # We know it's "TBD_UPDATE_ME" but let's prefill if they typed something partial 
        # Actually it's better to just leave it blank for faster fresh typing
        self.oneclick_input.focus()
        
        # Enable buttons
        self.btn_save.configure(state="normal")
        self.btn_skip.configure(state="normal")
        self.btn_delete.configure(state="normal")
        self.btn_deep_edit.configure(state="normal")

    def skip(self):
        self.current_index += 1
        self.display_current_item()

    def delete_item(self):
        item = self.queue[self.current_index]
        item_id = item.get('id')
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to permanently delete ID: {item_id}?")
        if not confirm:
            return
            
        cat_file = item.get('category_file', '') + '.yaml'
        target_yaml_path = os.path.join(self.categories_path, cat_file)
        
        if os.path.exists(target_yaml_path):
            with open(target_yaml_path, 'r', encoding='utf-8') as f:
                existing_data = yaml.safe_load(f) or []

            new_data = [i for i in existing_data if i.get('id') != item_id]

            with open(target_yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(new_data, f, sort_keys=False, allow_unicode=True)
                
        # Remove from local queue
        self.queue.pop(self.current_index)
        self.display_current_item()

    def open_full_editor(self):
        item = self.queue[self.current_index]
        
        # The DatabaseManager is a Toplevel meant to open on top of another CTOk window.
        # We instantiate it and trigger load_for_edit
        editor = DatabaseManager(self, self.db_loader)
        
        # The load_for_edit function normally expects a Toplevel details window to destroy.
        # We pass a dummy class to safely absorb the .destroy() call so it doesn't break the UI.
        class DummyWindow:
            def destroy(self): pass
            
        editor.load_for_edit(item.get('id'), DummyWindow())
        
        # We need to wait until the editor is closed to refresh queue.
        # However, customTkinter doesn't fully block nicely like wait_window natively in all setups.
        self.wait_window(editor)
        
        # Once closed, we refresh the queue to reflect deep edits.
        self.refresh_queue()

    def save_and_next(self):
        new_desc = self.oneclick_input.get().strip()
        if not new_desc:
            messagebox.showwarning("Missing Input", "Please enter a valid oneclick description. Or press Skip.")
            return
            
        item = self.queue[self.current_index]
        item_id = item.get('id')
        cat_file = item.get('category_file', '') + '.yaml'
        target_yaml_path = os.path.join(self.categories_path, cat_file)
        
        if not os.path.exists(target_yaml_path):
            messagebox.showerror("File Error", f"YAML file {cat_file} not found.")
            return
            
        # Read the raw yaml array
        try:
            with open(target_yaml_path, 'r', encoding='utf-8') as f:
                existing_data = yaml.safe_load(f) or []
            
            # Find and update
            updated = False
            for doc_item in existing_data:
                if doc_item.get('id') == item_id:
                    doc_item['oneclick_description'] = new_desc
                    doc_item['verified_oneclick'] = True
                    updated = True
                    break
                    
            if not updated:
                messagebox.showerror("Error", "Item ID not found in the original yaml. Skipping.")
                self.skip()
                return

            # Save back
            with open(target_yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(existing_data, f, sort_keys=False, allow_unicode=True)
                
            # Pop item from local queue and display next
            self.queue.pop(self.current_index)
            # Do NOT increment current_index because popping shifted everything left!
            self.display_current_item()
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save: {e}")

if __name__ == "__main__":
    app = DataFixerApp()
    app.mainloop()
