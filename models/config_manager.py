import os
import json
import sys

# Try importing secrets_env from the correct location depending on how the app is run
try:
    # When running as standard script or PyInstaller
    import secrets_env
    KITCHEN_TOKEN = getattr(secrets_env, "KITCHEN_TEAM_TOKEN", "")
    BATH_TOKEN = getattr(secrets_env, "BATH_TEAM_TOKEN", "")
    READ_ONLY_TOKEN = getattr(secrets_env, "GITHUB_READ_ONLY_TOKEN", "")
    GEMINI_KEY = getattr(secrets_env, "GEMINI_API_KEY", "")
except ImportError:
    KITCHEN_TOKEN = ""
    BATH_TOKEN = ""
    READ_ONLY_TOKEN = ""
    GEMINI_KEY = ""

class ConfigManager:
    """
    Manages application settings stored in a local settings.json file.
    """
    CONFIG_FILE = "settings.json"
    #GITHUB_READ_ONLY_TOKEN = READ_ONLY_TOKEN
    
    TEAM_PRESETS = {
        "Kitchen Team": {
            "github_owner": "BathPC",
            "github_repo": "material-confirmation-db-kitchen",
            "github_token": KITCHEN_TOKEN,
            "role": "user",
            "cover_image_filename": "Kitchen Document Cover Page.png"
        },
        "Bath Team": {
            "github_owner": "BathPC",
            "github_repo": "material-confirmation-db",
            "github_token": BATH_TOKEN,
            "role": "user",
            "cover_image_filename": "Bath Document Cover Page.png"
        }
    }
    
    DEFAULT_SETTINGS = {
        "llm_model": "llama3.1",
        "show_ollama_window": True,
        "cover_image_filename": "Default Cover Page.png",
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
        "github_owner": "BathPC",
        "github_repo": "material-confirmation-db",
        "github_token": "",
        "github_branch": "main",
        "gemini_api_key": GEMINI_KEY
    }

    @classmethod
    def apply_preset(cls, team_name: str) -> None:
        """Applies a preset configuration and saves it to disk."""
        if team_name in cls.TEAM_PRESETS:
            settings = cls.load()
            settings.update(cls.TEAM_PRESETS[team_name])
            cls.save(settings)
    
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
