import os
import sys
import shutil
import subprocess
import requests
import json

class OllamaUtils:
    """
    Utility class to manage the Ollama service locally.
    Provides OS-aware process management and interacts with the Ollama REST API.
    """
    
    _process = None  # Holds the Popen instance if we started it
    
    @staticmethod
    def is_installed() -> bool:
        """Checks if the 'ollama' executable is available in the system PATH."""
        return shutil.which("ollama") is not None
        
    @staticmethod
    def is_running(host: str = "http://localhost:11434") -> bool:
        """Checks if the Ollama API is responding."""
        try:
            response = requests.get(f"{host}/api/tags", timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    @classmethod
    def start_server(cls, show_window: bool = True) -> bool:
        """
        Spawns the 'ollama serve' process.
        If show_window is True (and on Windows), opens a new console window.
        """
        if cls.is_running():
            return True
            
        try:
            # We use CREATE_NEW_CONSOLE on Windows to show the user the terminal, if requested
            creationflags = 0
            if sys.platform == "win32":
                if show_window:
                    creationflags = subprocess.CREATE_NEW_CONSOLE
                else:
                    creationflags = subprocess.CREATE_NO_WINDOW
            
            # Start the background process
            cls._process = subprocess.Popen(
                ["ollama", "serve"],
                creationflags=creationflags
            )
            return True
        except Exception as e:
            print(f"[OllamaUtils] Failed to start Ollama: {e}")
            return False

    @classmethod
    def stop_server(cls, force_os_kill: bool = False) -> None:
        """
        Terminates Ollama.
        Always kills the tracked process if we spawned it.
        If force_os_kill is True, uses OS-level kill to be sure (kills any instance).
        """
        # Try to terminate the specific process we spawned
        if cls._process is not None:
            try:
                cls._process.terminate()
                cls._process.wait(timeout=2)
            except Exception:
                pass
            cls._process = None

        if force_os_kill:
            # To be absolutely sure and free memory, do an OS-level kill
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/IM", "ollama.exe", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    # Also kill ollama app.exe just in case the desktop app was running
                    subprocess.run(["taskkill", "/IM", "ollama app.exe", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    subprocess.run(["killall", "ollama"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"[OllamaUtils] Error during OS-level kill: {e}")

    @staticmethod
    def get_models(host: str = "http://localhost:11434") -> list:
        """Returns a list of installed model names."""
        if not OllamaUtils.is_running(host):
            return []
            
        try:
            response = requests.get(f"{host}/api/tags", timeout=2)
            if response.status_code == 200:
                data = response.json()
                return [m.get("name") for m in data.get("models", [])]
            return []
        except requests.exceptions.RequestException:
            return []

    @staticmethod
    def delete_model(model_name: str, host: str = "http://localhost:11434") -> bool:
        """Deletes a model via the REST API."""
        try:
            response = requests.delete(f"{host}/api/delete", json={"name": model_name}, timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    @staticmethod
    def pull_model(model_name: str, progress_callback, host: str = "http://localhost:11434"):
        """
        Pulls a model using the streaming API and reports progress via callback.
        progress_callback should accept (status_str, percent_float).
        """
        try:
            response = requests.post(
                f"{host}/api/pull", 
                json={"name": model_name}, 
                stream=True,
                timeout=10
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    data = json.loads(line.decode('utf-8'))
                    status = data.get("status", "Downloading...")
                    
                    # Calculate percentage if total and completed are present
                    total = data.get("total", 0)
                    completed = data.get("completed", 0)
                    percent = 0.0
                    if total > 0:
                        percent = (completed / total) * 100
                        
                    progress_callback(status, percent)
                    
            return True
        except requests.exceptions.RequestException as e:
            print(f"[OllamaUtils] Error pulling model {model_name}: {e}")
            return False
