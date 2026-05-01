import customtkinter as ctk
import tkinter.messagebox as messagebox
import webbrowser
import threading
import os
import shutil
from tkinter import filedialog
from ollama_utils import OllamaUtils
from config_manager import ConfigManager

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Settings")
        
        # Load window geometry from config
        width = ConfigManager.get("settings_window_width")
        height = ConfigManager.get("settings_window_height")
        x = ConfigManager.get("settings_window_x")
        y = ConfigManager.get("settings_window_y")
        is_maximized = ConfigManager.get("settings_window_maximized")

        self.geometry(f"{width}x{height}+{x}+{y}")
        if is_maximized:
            self.after(200, lambda: self.state('zoomed'))
            
        # Make it modal
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_frame = ctk.CTkScrollableFrame(self)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.loading_lbl = ctk.CTkLabel(self.main_frame, text="Loading settings...", font=ctk.CTkFont(size=14))
        self.loading_lbl.pack(pady=(20, 10))
        self.progress = ctk.CTkProgressBar(self.main_frame, mode="indeterminate")
        self.progress.pack(pady=10)
        self.progress.start()
        
        threading.Thread(target=self._load_data, daemon=True).start()

    def on_closing(self):
        # Save window state before exiting
        is_maximized = (self.state() == 'zoomed')
        ConfigManager.set("settings_window_maximized", is_maximized)
        
        if not is_maximized:
            ConfigManager.set("settings_window_width", self.winfo_width())
            ConfigManager.set("settings_window_height", self.winfo_height())
            ConfigManager.set("settings_window_x", self.winfo_x())
            ConfigManager.set("settings_window_y", self.winfo_y())
            
        self.destroy()

    def _load_data(self):
        is_installed = OllamaUtils.is_installed()
        is_running = OllamaUtils.is_running()
        models = OllamaUtils.get_models() if is_running else []
        
        if self.winfo_exists():
            self.after(0, lambda: self._on_data_loaded(is_installed, is_running, models))

    def _on_data_loaded(self, is_installed, is_running, models):
        self.loading_lbl.destroy()
        self.progress.stop()
        self.progress.destroy()
        
        self.build_ollama_section(is_installed, is_running, models)
        self.build_pdf_section()
        
    def build_ollama_section(self, is_installed, is_running, models):
        # Section Title
        title_lbl = ctk.CTkLabel(self.main_frame, text="Requirements & Ollama Settings", font=ctk.CTkFont(size=18, weight="bold"))
        title_lbl.pack(anchor="w", pady=(10, 20))

        # Status Frame
        status_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        status_frame.pack(fill="x", pady=5)
        
        inst_color = "green" if is_installed else "red"
        run_color = "green" if is_running else "red"
        
        self.lbl_installed = ctk.CTkLabel(status_frame, text=f"Installed: {'Yes' if is_installed else 'No'}", text_color=inst_color)
        self.lbl_installed.pack(side="left", padx=10)
        
        self.lbl_running = ctk.CTkLabel(status_frame, text=f"Running: {'Yes' if is_running else 'No'}", text_color=run_color)
        self.lbl_running.pack(side="left", padx=10)

        # Actions Frame
        actions_frame = ctk.CTkFrame(self.main_frame)
        actions_frame.pack(fill="x", pady=10, ipadx=10, ipady=10)
        
        if not is_installed:
            btn_download = ctk.CTkButton(actions_frame, text="⬇️ Download Ollama", command=lambda: webbrowser.open("https://ollama.com/download"))
            btn_download.pack(pady=5)
        else:
            # Show/Hide Window Toggle
            self.show_window_var = ctk.BooleanVar(value=ConfigManager.get("show_ollama_window"))
            switch_window = ctk.CTkSwitch(actions_frame, text="Show terminal when starting Ollama", variable=self.show_window_var, command=self.save_show_window_setting)
            switch_window.pack(pady=5)

            # Start / Stop buttons
            btn_frame = ctk.CTkFrame(actions_frame, fg_color="transparent")
            btn_frame.pack(pady=5)
            
            self.btn_start = ctk.CTkButton(btn_frame, text="▶️ Start Service", fg_color="green", hover_color="darkgreen", command=self.start_ollama, state="disabled" if is_running else "normal")
            self.btn_start.pack(side="left", padx=5)
            
            self.btn_stop = ctk.CTkButton(btn_frame, text="⏹️ Kill Service", fg_color="red", hover_color="darkred", command=self.stop_ollama, state="normal" if is_running else "disabled")
            self.btn_stop.pack(side="left", padx=5)

            # Model Management Section
            ctk.CTkLabel(actions_frame, text="Model Management", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5))
            
            self.model_var = ctk.StringVar(value=ConfigManager.get("llm_model"))
            self.combo_model = ctk.CTkOptionMenu(actions_frame, variable=self.model_var, command=self.save_model_selection)
            self.combo_model.pack(pady=5)
            self._update_model_list_ui(models)

            pull_frame = ctk.CTkFrame(actions_frame, fg_color="transparent")
            pull_frame.pack(pady=10)
            
            self.entry_pull = ctk.CTkEntry(pull_frame, placeholder_text="e.g. llama3.1")
            self.entry_pull.pack(side="left", padx=5)
            
            self.btn_pull = ctk.CTkButton(pull_frame, text="⬇️ Pull/Update", command=self.pull_model)
            self.btn_pull.pack(side="left", padx=5)
            
            self.btn_delete = ctk.CTkButton(actions_frame, text="🗑️ Delete Selected Model", fg_color="#8B0000", hover_color="#600000", command=self.delete_model)
            self.btn_delete.pack(pady=10)
            
            # Progress bar for pulling
            self.pull_status_lbl = ctk.CTkLabel(actions_frame, text="")
            self.pull_status_lbl.pack()
            self.pull_progress = ctk.CTkProgressBar(actions_frame)
            self.pull_progress.set(0)
            self.pull_progress.pack(fill="x", padx=20, pady=5)
            self.pull_progress.pack_forget()

    def save_show_window_setting(self):
        ConfigManager.set("show_ollama_window", self.show_window_var.get())

    def save_model_selection(self, choice):
        ConfigManager.set("llm_model", choice)

    def refresh_status(self):
        is_running = OllamaUtils.is_running()
        run_color = "green" if is_running else "red"
        self.lbl_running.configure(text=f"Running: {'Yes' if is_running else 'No'}", text_color=run_color)
        
        if hasattr(self, 'btn_start'):
            self.btn_start.configure(state="disabled" if is_running else "normal")
            self.btn_stop.configure(state="normal" if is_running else "disabled")
            self.refresh_model_list()

    def refresh_model_list(self):
        models = OllamaUtils.get_models()
        self._update_model_list_ui(models)
        
    def _update_model_list_ui(self, models):
        if not models:
            self.combo_model.configure(values=["No models found"])
            return
            
        self.combo_model.configure(values=models)
        current = self.model_var.get()
        if current not in models:
            self.model_var.set(models[0])
            self.save_model_selection(models[0])

    def start_ollama(self):
        self.btn_start.configure(state="disabled")
        show = self.show_window_var.get()
        OllamaUtils.start_server(show_window=show)
        self.after(2000, self.refresh_status)

    def stop_ollama(self):
        self.btn_stop.configure(state="disabled")
        OllamaUtils.stop_server(force_os_kill=True)
        self.after(2000, self.refresh_status)
        
    def delete_model(self):
        model = self.model_var.get()
        if model and model != "No models found":
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {model}?"):
                if OllamaUtils.delete_model(model):
                    messagebox.showinfo("Success", f"Model {model} deleted.")
                    self.refresh_model_list()
                else:
                    messagebox.showerror("Error", f"Failed to delete {model}.")

    def pull_model(self):
        model_name = self.entry_pull.get().strip()
        if not model_name:
            messagebox.showwarning("Warning", "Please enter a model name to pull.")
            return
            
        self.btn_pull.configure(state="disabled")
        self.pull_progress.pack(fill="x", padx=20, pady=5)
        self.pull_status_lbl.configure(text=f"Starting pull for {model_name}...")
        
        def progress_cb(status_msg, percent):
            if self.winfo_exists():
                self.after(0, lambda: self.pull_status_lbl.configure(text=f"{status_msg} ({percent:.1f}%)"))
                self.after(0, lambda: self.pull_progress.set(percent / 100.0))
                
        def pull_task():
            success = OllamaUtils.pull_model(model_name, progress_cb)
            if self.winfo_exists():
                self.after(0, self._on_pull_complete, success, model_name)
                
        threading.Thread(target=pull_task, daemon=True).start()
        
    def _on_pull_complete(self, success, model_name):
        self.btn_pull.configure(state="normal")
        self.pull_progress.pack_forget()
        if success:
            self.pull_status_lbl.configure(text=f"Successfully pulled {model_name}!")
            self.refresh_model_list()
            # Select the newly pulled model
            self.model_var.set(model_name)
            self.save_model_selection(model_name)
        else:
            self.pull_status_lbl.configure(text=f"Failed to pull {model_name}.")

    def build_pdf_section(self):
        title_lbl = ctk.CTkLabel(self.main_frame, text="PDF Settings", font=ctk.CTkFont(size=18, weight="bold"))
        title_lbl.pack(anchor="w", pady=(20, 10))

        pdf_frame = ctk.CTkFrame(self.main_frame)
        pdf_frame.pack(fill="x", pady=5, ipadx=10, ipady=10)
        
        ctk.CTkLabel(pdf_frame, text="Cover Image:").pack(side="left", padx=10)
        
        self.lbl_cover_name = ctk.CTkLabel(pdf_frame, text=ConfigManager.get("cover_image_filename"))
        self.lbl_cover_name.pack(side="left", padx=10)
        
        btn_pick_cover = ctk.CTkButton(pdf_frame, text="Pick New Cover", command=self.pick_cover_image)
        btn_pick_cover.pack(side="right", padx=10)

    def pick_cover_image(self):
        file_path = filedialog.askopenfilename(title="Select Cover Image", filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
        if file_path:
            filename = os.path.basename(file_path)
            dest_path = os.path.join("database", "assets", filename)
            
            try:
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                if os.path.abspath(file_path) != os.path.abspath(dest_path):
                    shutil.copy2(file_path, dest_path)
                    
                ConfigManager.set("cover_image_filename", filename)
                self.lbl_cover_name.configure(text=filename)
                messagebox.showinfo("Success", f"Cover image updated to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import image: {e}")
