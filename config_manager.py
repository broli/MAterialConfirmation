import os
import json

class ConfigManager:
    """
    Manages application settings stored in a local settings.json file.
    """
    CONFIG_FILE = "settings.json"
    
    DEFAULT_SETTINGS = {
        "llm_model": "llama3",
        "show_ollama_window": True,
        "cover_image_filename": "Bath Document Cover Page.png"
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
