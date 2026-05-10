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
from openai import OpenAI
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


class GeminiClient:
    """
    Lightweight wrapper for interacting with the Google Gemini API,
    powered by Pydantic + Instructor for structured, validated outputs.
    Uses the OpenAI API compatibility layer.
    """

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        log_callback=None,
        debug_mode: bool = False,
        log_dir: str = "logs",
    ):
        self.api_key = api_key or ConfigManager.get("gemini_api_key")
        self.model = model or ConfigManager.get("gemini_model") or "gemini-3.0-flash"
        self.log_callback = log_callback
        self.debug_mode = debug_mode
        self.log_dir = log_dir

        if not self.api_key:
            raise ValueError("Gemini API key is required. Please set it in Settings (Admin).")

        # Instructor-patched OpenAI client -> Gemini API
        self.client = instructor.from_openai(
            OpenAI(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=self.api_key,
            ),
            mode=instructor.Mode.JSON,
        )

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
            raise RuntimeError(f"Gemini API Extraction Error: {exc}")
