"""
llm_service.py
==============
Wrapper for the local Ollama instance using Instructor + Pydantic.

Debug logging
-------------
Pass ``debug_mode=True`` to enable per-call file logs in ``logs/``.
Each session creates one log file:  ``logs/ollama_YYYYMMDD_HHMMSS.log``

The log records for every Ollama call:
  - Timestamp, sequential call number
  - Model, hints (section / category)
  - Full prompt text
  - Elapsed time
  - Full JSON response (or error message)
"""

import time
import logging
import requests
from datetime import datetime
from openai import OpenAI
import instructor
from schema.contract_item import ContractItem


# ─── Module-level debug logger (shared across all LocalLLMClient instances) ──
_ollama_logger: logging.Logger | None = None
_call_counter = 0   # global call sequence number (for log readability)


def _get_ollama_logger(log_dir: str = "logs") -> logging.Logger:
    """
    Return the module-level Ollama debug logger, creating it on first call.
    Writes to logs/ollama_YYYYMMDD_HHMMSS.log.
    """
    global _ollama_logger
    if _ollama_logger is None:
        import os
        os.makedirs(log_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(log_dir, f"ollama_{stamp}.log")

        logger = logging.getLogger("OllamaDebug")
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(fh)

        logger.info(f"=== Ollama Debug Log — Session started {datetime.now().isoformat()} ===\n")
        _ollama_logger = logger
    return _ollama_logger


class LocalLLMClient:
    """
    Lightweight wrapper for interacting with a local Ollama instance,
    powered by Pydantic + Instructor for structured, validated outputs.

    Parameters
    ----------
    host : str
        Base URL of the Ollama API server.
    model : str
        Name of the model to use (must be pulled in Ollama).
    log_callback : callable | None
        Optional ``fn(str)`` called with each log line.  Used by the batch
        PDF UI to display real-time Ollama traffic in its console widget.
    debug_mode : bool
        When True, every request and response is written to a timestamped
        log file in the ``logs/`` directory.
    log_dir : str
        Directory where the debug log file is created.
    """

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = None,
        log_callback=None,
        debug_mode: bool = False,
        log_dir: str = "logs",
    ):
        self.host        = host
        self._model_override = model
        self.log_callback = log_callback
        self.debug_mode  = debug_mode
        self.log_dir     = log_dir

        # Instructor-patched OpenAI client → Ollama's local endpoint
        self.client = instructor.from_openai(
            OpenAI(
                base_url=f"{self.host}/v1",
                api_key="ollama",   # required by the OpenAI client; ignored by Ollama
            ),
            mode=instructor.Mode.JSON,
        )

    @property
    def model(self) -> str:
        """Dynamically fetch the model from config unless overridden during init."""
        if self._model_override is not None:
            return self._model_override
        from config_manager import ConfigManager
        return ConfigManager.get("llm_model")

    # ──────────────────────────────────────────────────────────────────────────
    # Logging helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        """Fire the UI console callback (if wired)."""
        if self.log_callback:
            self.log_callback(msg)

    def _file_log(self, msg: str) -> None:
        """Write to the debug log file (only when debug_mode is True)."""
        if self.debug_mode:
            _get_ollama_logger(self.log_dir).debug(msg)

    def _log_both(self, msg: str) -> None:
        """Write to both the UI callback and the file logger."""
        self._log(msg)
        self._file_log(msg)

    # ──────────────────────────────────────────────────────────────────────────
    # Connection check
    # ──────────────────────────────────────────────────────────────────────────

    def check_connection(self) -> tuple[bool, str]:
        """Verify that the Ollama service is running and the model is available."""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=3)
            if response.status_code == 200:
                models = [m["name"] for m in response.json().get("models", [])]
                if not any(m.startswith(self.model) for m in models):
                    return False, f"Model '{self.model}' not found in Ollama."
                return True, "Connected successfully."
            return False, f"Status code {response.status_code}."
        except requests.exceptions.RequestException as e:
            return False, f"Connection failed: {e}"

    # ──────────────────────────────────────────────────────────────────────────
    # Core extraction
    # ──────────────────────────────────────────────────────────────────────────

    def extract_product_fields(
        self,
        raw_text: str,
        hint_category: str | None = None,
        hint_section: str | None = None,
    ) -> ContractItem:
        """
        Parse a raw PDF description into a validated :class:`ContractItem`.

        Parameters
        ----------
        raw_text : str
            The concatenated description string from the contract PDF column.
        hint_category : str | None
            Pre-extracted category from the PDF column (e.g. ``"Shower Bases"``).
            When provided the LLM is told to use it verbatim and focus only
            on brand, finish, and dimensions — fewer tokens, faster response.
        hint_section : str | None
            Pre-extracted section (e.g. ``"Bath"``, ``"Kitchen"``).

        Returns
        -------
        ContractItem
            Pydantic-validated structured product attributes.

        Raises
        ------
        RuntimeError
            If the Ollama call fails after max retries.
        """
        global _call_counter
        _call_counter += 1
        call_num = _call_counter

        # ── Build hint context ────────────────────────────────────────────────
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
            "Example: {\"category\": \"Shower Bases\", \"base_item\": \"...\", \"brand\": \"...\", "
            "\"finish\": \"Matte Black\", \"dimensions\": {\"width\": \"60\", \"depth\": \"30\"}}"
        )
        user_content = (
            f"Extract structural information from this raw text:\n\n\"{raw_text}\""
            + known_context
        )

        # ── Pre-call log ──────────────────────────────────────────────────────
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        req_header = (
            f"\n{'='*60}\n"
            f"[{ts}]  CALL #{call_num}  →  {self.model}\n"
            f"HINTS   : section={hint_section!r}, category={hint_category!r}\n"
            f"TEXT    : {raw_text[:200]}{'...' if len(raw_text) > 200 else ''}\n"
            f"{'='*60}"
        )
        self._log_both(req_header)

        # ── Timed call ────────────────────────────────────────────────────────
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
            raise RuntimeError(f"Ollama Extraction Error: {exc}")


# ─── CLI self-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing connection to Ollama...")
    llm = LocalLLMClient(model=None, debug_mode=True)

    success, msg = llm.check_connection()
    if success:
        print("Connected! Testing extraction...")
        try:
            test_str = 'Bath Accessories Grab Bars Traditional 16" Traditional Grab Bar Matte Black'
            res = llm.extract_product_fields(
                test_str,
                hint_section="Bath",
                hint_category="Accessories",
            )
            print(f"Base Item : {res.base_item}")
            print(f"Finish    : {res.finish}")
            print(f"Dimensions: {res.dimensions}")
        except Exception as e:
            print(f"Test failed: {e}")
    else:
        print(f"Ollama Connection Failed: {msg}")
        print("Ensure Ollama is running and model is pulled ('ollama run llama3.1').")
