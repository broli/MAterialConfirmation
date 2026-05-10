"""
gemini_service.py
=================
Wrapper for the Gemini API using Instructor + Pydantic via the OpenAI compatibility layer.

Debug logging
-------------
Pass ``debug_mode=True`` to enable per-call file logs in ``logs/``.
Each session creates one log file:  ``logs/gemini_YYYYMMDD_HHMMSS.log``
"""

import time
import logging
from datetime import datetime
from openai import OpenAI, RateLimitError
import instructor
from schema.contract_item import ContractItem
from models.config_manager import ConfigManager

_gemini_logger: logging.Logger | None = None
_call_counter = 0

def _get_gemini_logger(log_dir: str = "logs") -> logging.Logger:
    global _gemini_logger
    if _gemini_logger is None:
        import os
        os.makedirs(log_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(log_dir, f"gemini_{stamp}.log")

        logger = logging.getLogger("GeminiDebug")
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(fh)

        logger.info(f"=== Gemini Debug Log — Session started {datetime.now().isoformat()} ===\n")
        _gemini_logger = logger
    return _gemini_logger


class QuotaExceededError(Exception):
    """Raised when the daily free quota is exhausted."""
    pass

class GeminiClient:
    """
    Lightweight wrapper for interacting with the Google Gemini API,
    powered by Pydantic + Instructor for structured, validated outputs.
    Uses the OpenAI API compatibility layer.
    """
    
    _available_models: list[str] = []

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        log_callback=None,
        model_status_callback=None,
        debug_mode: bool = False,
        log_dir: str = "logs",
    ):
        self.api_key = api_key or ConfigManager.get("gemini_api_key")
        self.model = model or ConfigManager.get("gemini_model") or "gemini-3.0-flash"
        self.log_callback = log_callback
        self.model_status_callback = model_status_callback
        self.debug_mode = debug_mode
        self.log_dir = log_dir

        if not self.api_key:
            raise ValueError("Gemini API key is required. Please set it in Settings (Admin).")

        # Instructor-patched OpenAI client -> Gemini API
        self.client = instructor.from_openai(
            OpenAI(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=self.api_key,
                max_retries=0, # Disable internal rate limit retries so we can waterfall immediately
            ),
            mode=instructor.Mode.JSON,
        )

    @classmethod
    def get_ranked_models(cls, api_key: str) -> list[str]:
        if cls._available_models:
            return list(cls._available_models)
            
        import urllib.request
        import json
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                
            models = []
            for model in data.get("models", []):
                methods = model.get("supportedGenerationMethods", [])
                name = model.get("name", "").replace("models/", "")
                
                # Filter criteria
                if "generateContent" not in methods:
                    continue
                # Exclude only strictly old models
                if name.startswith("gemini-1.0") or name == "gemini-pro" or "vision" in name:
                    continue
                if "gemma" in name or "learnlm" in name:
                    continue
                    
                models.append(name)
                
            # Ranking heuristic
            def rank_score(m: str):
                score = 0
                if "gemini-3.1" in m: score += 1000
                elif "gemini-3.0" in m: score += 900
                elif "gemini-2.5" in m: score += 800
                elif "gemini-2.0" in m: score += 700
                elif "gemini-1.5" in m: score += 600
                
                if "pro" in m: score += 50
                elif "flash" in m: score += 40
                elif "lite" in m: score += 30
                
                # Penalize preview/experimental
                if "preview" in m or "experimental" in m: score -= 5
                
                return score
                
            models.sort(key=rank_score, reverse=True)
            cls._available_models = models
            return models
        except Exception:
            # Fallback if API fails
            return ["gemini-3.0-flash", "gemini-1.5-flash"]

    def _log(self, msg: str) -> None:
        if self.log_callback:
            self.log_callback(msg)

    def _file_log(self, msg: str) -> None:
        if self.debug_mode:
            _get_gemini_logger(self.log_dir).debug(msg)

    def _log_both(self, msg: str) -> None:
        self._log(msg)
        self._file_log(msg)

    def extract_product_fields(
        self,
        raw_text: str,
        hint_category: str | None = None,
        hint_section: str | None = None,
    ) -> ContractItem:
        global _call_counter
        _call_counter += 1
        call_num = _call_counter

        known_context = ""
        if hint_section or hint_category:
            parts = []
            if hint_section:
                parts.append(f"Section='{hint_section}'")
            if hint_category:
                parts.append(f"Category='{hint_category}'")
            known_context = (
                f"\n\nPre-extracted context from document structure: {', '.join(parts)}. "
                "Use these as-is for the 'category' field — do NOT re-derive them. "
                "Focus your extraction on: brand, finish, and dimensions only."
            )

        system_msg = (
            "You are a strict data extraction AI. "
            "Extract brand, finish, and dimensions from the provided text. "
            "If a category is pre-provided in the context, copy it exactly into the 'category' field. "
            "IMPORTANT: Return the JSON object directly. DO NOT wrap in a 'properties' key. "
            "If you cannot determine a field, return 'UNKNOWN'."
        )
        user_content = (
            f"Extract structural information from this raw text:\n\n\"{raw_text}\""
            + known_context
        )

        models_to_try = self.get_ranked_models(self.api_key)
        if not models_to_try:
            raise RuntimeError("No compatible Gemini models found.")
            
        last_error = None
        for model_name in models_to_try:
            self.model = model_name
            if self.model_status_callback:
                self.model_status_callback(f"Active model: {model_name}")
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            req_header = (
                f"\n{'='*60}\n"
                f"[{ts}]  CALL #{call_num}  →  {self.model}\n"
                f"HINTS   : section={hint_section!r}, category={hint_category!r}\n"
                f"TEXT    : {raw_text[:200]}{'...' if len(raw_text) > 200 else ''}\n"
                f"{'='*60}"
            )
            self._log_both(req_header)

            t0 = time.perf_counter()
            try:
                # Let instructor retry parsing/validation errors 2 times. 
                # Network/Rate limits bubble up because max_retries=0 on OpenAI client.
                result = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user",   "content": user_content},
                    ],
                    response_model=ContractItem,
                    max_retries=2,
                )
                elapsed = time.perf_counter() - t0

                resp_msg = (
                    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]  "
                    f"CALL #{call_num} RESPONSE  ({elapsed:.2f}s)\n"
                    f"{result.model_dump_json(indent=2)}\n"
                )
                self._log_both(resp_msg)
                return result

            except Exception as exc:
                elapsed = time.perf_counter() - t0
                err_msg = (
                    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]  "
                    f"CALL #{call_num} ERROR  ({elapsed:.2f}s)\n"
                    f"{exc}\n"
                )
                self._log_both(err_msg)
                
                # Check for rate limit or quota
                err_str = str(exc).lower()
                cause = getattr(exc, "__cause__", exc) or exc
                
                is_rate_limit = (
                    isinstance(cause, RateLimitError) or 
                    isinstance(exc, RateLimitError) or 
                    "429" in err_str or 
                    "resource_exhausted" in err_str or 
                    "quota" in err_str
                )
                
                if is_rate_limit:
                    self._log_both(f"Rate limit or quota hit for {model_name}. Trying next model...")
                    if self.model_status_callback:
                        self.model_status_callback(f"Model {model_name} maxed. Dropping from pool...")
                    
                    # Permanently drop this model from the available pool so we don't loop on it
                    if model_name in self.__class__._available_models:
                        self.__class__._available_models.remove(model_name)
                        
                    last_error = exc
                    continue
                    
                raise RuntimeError(f"Gemini API Extraction Error: {exc}")

        last_err_str = str(last_error).lower()
        if "429" in last_err_str or "quota" in last_err_str or "resource_exhausted" in last_err_str:
            raise QuotaExceededError(f"All Gemini models exhausted their daily free quota or rate limits.")
            
        raise RuntimeError(f"All Gemini models exhausted. Last error: {last_error}")
