import os
import json

class ConfigManager:
    """
    Manages application settings stored in a local settings.json file.
    """
    CONFIG_FILE = "settings.json"
    
    DEFAULT_SETTINGS = {
        "llm_model": "llama3.1",
        "show_ollama_window": True,
        "cover_image_filename": "Bath Document Cover Page.png",
        "window_maximized": True,
        "window_width": 1100,
        "window_height": 750,
        "window_x": 100,
        "window_y": 100,
        "batch_window_maximized": True,
        "batch_window_width": 1100,
        "batch_window_height": 700,
        "batch_window_x": 150,
        "batch_window_y": 150,
        "db_window_maximized": True,
        "db_window_width": 1100,
        "db_window_height": 750,
        "db_window_x": 150,
        "db_window_y": 150,
        "settings_window_maximized": False,
        "settings_window_width": 550,
        "settings_window_height": 650,
        "settings_window_x": 200,
        "settings_window_y": 200,
        "last_pdf_dir": "",
        "role": "user",
        "github_owner": "YOUR_COMPANY_GITHUB_USERNAME",
        "github_repo": "material-confirmation-db",
        "github_token": ""
    }
    
    @classmethod
    def load(cls) -> dict:
        """Loads settings from disk, applying defaults for missing keys."""
        if not os.path.exists(cls.CONFIG_FILE):
            return cls.DEFAULT_SETTINGS.copy()
            
        try:
            with open(cls.CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Merge with defaults to ensure all keys exist
            settings = cls.DEFAULT_SETTINGS.copy()
            settings.update(data)
            return settings
            
        except Exception as e:
            print(f"[ConfigManager] Error loading settings: {e}")
            return cls.DEFAULT_SETTINGS.copy()
            
    @classmethod
    def save(cls, settings: dict) -> None:
        """Saves settings to disk."""
        try:
            with open(cls.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"[ConfigManager] Error saving settings: {e}")

    @classmethod
    def get(cls, key: str):
        """Helper to get a single setting."""
        return cls.load().get(key)
        
    @classmethod
    def set(cls, key: str, value) -> None:
        """Helper to set a single setting."""
        settings = cls.load()
        settings[key] = value
        cls.save(settings)
