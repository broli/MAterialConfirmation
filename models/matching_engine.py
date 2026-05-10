"""
matching_engine.py
==================
Provides all database-matching business logic for the PKB ERP system.

This module intentionally has NO dependency on any UI toolkit (tkinter, customtkinter, etc.).
It is a pure Python backend service that can be tested, extended, or replaced independently.

Public API for the UI layer
----------------------------
Use `MatchService` — it is the single entry point for anything that needs to find a
database item from a piece of extracted text.

Do NOT call `MatchingEngine` directly from the UI.  It is a low-level text-search
utility consumed by `MatchService`.

Classes
-------
- MatchingEngine  : Low-level fuzzy-text search against the catalog index.
- MatchService    : High-level orchestrator — handles sessions, confirmed items,
                    ignored routing tags, and color-code calculation.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from threading import Lock

from rapidfuzz import process, fuzz
from schema.contract_item import ContractItem
from models.llm_service import LocalLLMClient
from models.gemini_service import GeminiClient
from models.config_manager import ConfigManager


# ---------------------------------------------------------------------------
# MatchDebugLogger — per-item diagnostic file logger
# ---------------------------------------------------------------------------

class MatchDebugLogger:
    """
    Writes a detailed per-item diagnostic block to
    ``logs/matching_YYYYMMDD_HHMMSS.log`` whenever debug_mode is enabled.

    Each block contains:
      - Raw PDF item fields (room, section, category, description, qty)
      - LLM-extracted ContractItem fields (base_item, brand, finish, dimensions)
      - Fuzzy search target string that was assembled
      - How many candidates survived the finish/dimension filters
      - Top-5 scored candidates with their DB oneclick_description strings
      - Final winner with confidence score and traffic-light color
    """

    _instance: "MatchDebugLogger | None" = None

    def __init__(self, log_dir: str = "logs"):
        os.makedirs(log_dir, exist_ok=True)
        stamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(log_dir, f"matching_{stamp}.log")

        self._logger = logging.getLogger(f"MatchDebug_{stamp}")
        self._logger.setLevel(logging.DEBUG)
        self._logger.propagate = False

        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(message)s"))
        self._logger.addHandler(fh)
        self._call_num = 0

        self._logger.info(
            f"=== Match Debug Log — Session {datetime.now().isoformat()} ===\n"
        )

    def log_resolution(
        self,
        item: dict,
        contract_item: "ContractItem | None",
        search_target: str,
        catalog_size: int,
        candidates_after_filter: dict,
        top_results: list,
        final_id: "str | None",
        confidence: float,
        color_code: str,
        confirmed: bool,
        is_ignored: bool,
        fast_path_used: bool = False,
    ) -> None:
        """
        Write one full diagnostic block for a single item resolution.

        Parameters
        ----------
        item : dict
            The raw PDF line item dict.
        contract_item : ContractItem | None
            The LLM-extracted structured data (None for confirmed items).
        search_target : str
            The string passed to RapidFuzz.
        catalog_size : int
            Total number of items in the catalog index.
        candidates_after_filter : dict
            ``{ item_id: oneclick_description }`` after finish/dim filtering.
        top_results : list
            List of ``(score, id, db_desc)`` tuples from RapidFuzz, top-5 only.
        final_id : str | None
            The winning match ID.
        confidence : float
            Confidence score (0–100).
        color_code : str
            Traffic-light color name.
        confirmed : bool
            Whether this item was already user-confirmed.
        is_ignored : bool
            Whether the winning DB entry has routing_tag=IGNORE.
        """
        self._call_num += 1
        n   = self._call_num
        sep = "=" * 70
        dash = "-" * 70

        lines = [
            f"\n{sep}",
            f"  MATCH #{n}  —  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"{sep}",
            "",
            "── 1. WHAT WE HAVE (PDF item) ──────────────────────────────────────",
            f"  Room     : {item.get('room', '')}",
            f"  Section  : {item.get('section', '')}",
            f"  Category : {item.get('category', '')}",
            f"  Qty/Unit : {item.get('qty', '')} {item.get('unit', '')}",
            f"  Raw Desc : {item.get('raw_description', '')}",
        ]

        if confirmed:
            lines += [
                "",
                "── 2. RESOLUTION PATH ──────────────────────────────────────────────",
                f"  ✅ ALREADY CONFIRMED by user — trusted stored match_id.",
                f"  Matched ID : {final_id}",
                f"  Confidence : 100% (forced)",
                f"  Color      : {color_code}",
            ]
        else:
            if fast_path_used:
                lines += [
                    "",
                    "── 2. LLM EXTRACTION ────────────────────────────────────────────────",
                    "  ⚡ BYPASSED (Fast Path hit on raw description)",
                    "",
                    "── 3. DATABASE FILTER ───────────────────────────────────────────────",
                    "  ⚡ BYPASSED",
                    "",
                    "── 4. FAST PATH SEARCH (token_set_ratio) ────────────────────────────",
                    f"  Search target : {search_target!r}",
                ]
            else:
                # LLM extraction block
                if contract_item:
                    dims_str = ", ".join(
                        f"{k}={v}" for k, v in (contract_item.dimensions or {}).items()
                    )
                    lines += [
                        "",
                        "── 2. LLM EXTRACTION (ContractItem) ─────────────────────────────────",
                        f"  base_item  : {contract_item.base_item}",
                        f"  category   : {contract_item.category}",
                        f"  brand      : {contract_item.brand}",
                        f"  finish     : {contract_item.finish}",
                        f"  dimensions : {dims_str or 'none'}",
                    ]
                else:
                    lines += [
                        "",
                        "── 2. LLM EXTRACTION ────────────────────────────────────────────────",
                        "  (LLM failed or not called)",
                    ]

                # Filter summary
                filtered_out = catalog_size - len(candidates_after_filter)
                lines += [
                    "",
                    "── 3. DATABASE FILTER ───────────────────────────────────────────────",
                    f"  Catalog size       : {catalog_size} items",
                    f"  Filtered out       : {filtered_out} items"
                    + (f" (finish={contract_item.finish!r})" if contract_item and contract_item.finish else "")
                    + (f" + dim constraints" if contract_item and contract_item.dimensions else ""),
                    f"  Candidates left    : {len(candidates_after_filter)} items",
                ]

                # Fuzzy search
                lines += [
                    "",
                    "── 4. FUZZY SEARCH (WRatio) ─────────────────────────────────────────",
                    f"  Search target : {search_target!r}",
                ]

            if top_results:
                lines.append("  Top matches   :")
                for rank, (score, mid, db_desc) in enumerate(top_results, 1):
                    marker = "  ★" if mid == final_id else "   "
                    lines.append(f"{marker} #{rank:2d}  {score:6.2f}%  [{mid}]  {db_desc[:80]}")
            else:
                lines.append("  No candidates to rank.")

            # Final verdict
            verdict_emoji = "🟢" if color_code == "green" else ("🟡" if color_code == "yellow" else "🔴")
            if is_ignored:
                verdict_emoji = "⚫"
            lines += [
                "",
                "── 5. VERDICT ───────────────────────────────────────────────────────",
                f"  {verdict_emoji}  Match ID   : {final_id or 'NO MATCH'}",
                f"     Confidence : {confidence:.1f}%",
                f"     Color      : {color_code}",
                f"     Ignored    : {is_ignored}",
            ]

        lines.append("")
        self._logger.debug("\n".join(lines))


# ---------------------------------------------------------------------------
# MatchingEngine — Low-level text search
# ---------------------------------------------------------------------------

class MatchingEngine:
    """
    Low-level fuzzy-text matcher.

    Builds an inverted index of { item_id -> oneclick_description } at
    construction time and exposes a single ``match_item`` lookup.

    This class has no knowledge of sessions, UI state, or user actions —
    it only answers the question "which catalog entry is most similar to
    this raw text string?".

    Attributes
    ----------
    THRESHOLD_HIGH : float
        Score that triggers a "green / confirmed" traffic-light colour.
    THRESHOLD_MID : float
        Minimum score for a "yellow / review" colour; below this is "red".
    """

    THRESHOLD_HIGH: float = 100.0
    THRESHOLD_MID:  float = 90.0

    def __init__(self, catalog: dict):
        """
        Build the fuzzy-match index from the master catalog.

        Parameters
        ----------
        catalog : dict
            The master catalog returned by ``CatalogLoader.load_all_categories()``.
            Shape: { item_id (str) -> item_data (dict) }
        """
        self.catalog = catalog

        # { search_key -> target_string } for RapidFuzz
        self._index: dict[str, str] = {}
        # { search_key -> actual_item_id } to resolve aliases back to the master catalog
        self._reverse_map: dict[str, str] = {}

        for item_id, item_data in catalog.items():
            desc = item_data.get("oneclick_description", "").strip()
            if not desc:
                desc = "TBD_UPDATE_ME"
            
            # Index the primary description
            primary_key = f"{item_id}_main"
            self._index[primary_key] = desc
            self._reverse_map[primary_key] = item_id
            
            # Index any known aliases
            aliases = item_data.get("aliases", [])
            if isinstance(aliases, list):
                for i, alias in enumerate(aliases):
                    alias_str = str(alias).strip()
                    if alias_str:
                        alias_key = f"{item_id}_alias_{i}"
                        self._index[alias_key] = alias_str
                        self._reverse_map[alias_key] = item_id

    # ------------------------------------------------------------------
    # Public search API
    # ------------------------------------------------------------------

    def fast_match(self, raw_description: str) -> list:
        """
        Attempt a high-speed token_set_ratio match against all catalog items.
        
        Returns
        -------
        list
            The top 2 match tuples: ``[(score, item_id, db_desc), ...]``
            Used by MatchService to evaluate the "Margin of Victory".
        """
        if not self._index or not raw_description:
            return []

        all_results = process.extract(
            raw_description,
            self._index,
            scorer=fuzz.token_set_ratio,
            limit=2,
        )
        
        # Sort descending and return in (score, actual_id, db_desc) format to match Slow Path
        results_sorted = sorted(all_results, key=lambda x: x[1], reverse=True)
        return [(score, self._reverse_map[s_key], db_desc) for db_desc, score, s_key in results_sorted]

    def match_item(
        self,
        contract_item: ContractItem,
        _return_candidates: bool = False,
    ) -> tuple:
        """
        Find the single best catalog entry for a parsed ContractItem.

        First strictly filters on finish and dimensions, then uses RapidFuzz
        on the remaining candidate pool.

        Parameters
        ----------
        contract_item : ContractItem
            Structured product fields extracted by the LLM.
        _return_candidates : bool
            Internal flag — when True, returns a 4-tuple that also includes
            the candidate dict (used by the debug logger in MatchService).
        """
        if not self._index:
            if _return_candidates:
                return None, None, 0.0, {}
            return None, None, 0.0

        candidates = {}
        for s_key, desc in self._index.items():
            item_id = self._reverse_map[s_key]
            item_data = self.catalog[item_id]

            # 1. Strict filter on Finish
            if contract_item.finish:
                db_printable = item_data.get("printable") or {}
                db_finish    = db_printable.get("finish", "")
                if db_finish and contract_item.finish.lower() not in db_finish.lower():
                    continue

            # 2. Strict filter on Dimensions
            if contract_item.dimensions:
                db_printable = item_data.get("printable") or {}
                db_dims      = db_printable.get("dimensions", {})
                if db_dims:
                    failed_dim = False
                    for dim_key, dim_val in contract_item.dimensions.items():
                        dim_str = str(dim_val).lower().replace('"', '').replace('in', '').strip()
                        found   = False
                        for db_k, db_val in db_dims.items():
                            db_str = str(db_val).lower().replace('"', '').replace('in', '').strip()
                            if dim_str in db_str or db_str in dim_str:
                                found = True
                                break
                        if not found:
                            failed_dim = True
                            break
                    if failed_dim:
                        continue

            candidates[s_key] = desc

        if not candidates:
            if _return_candidates:
                return None, None, 0.0, {}
            return None, None, 0.0

        # 3. Fuzzy Match
        search_target = contract_item.base_item or ""
        if contract_item.category:
            search_target = f"{contract_item.category} {search_target}"
        if contract_item.brand:
            search_target = f"{contract_item.brand} {search_target}"

        all_results = process.extract(
            search_target,
            candidates,
            scorer=fuzz.WRatio,
            limit=None,
        )

        if all_results:
            # all_results is list of (db_desc, score, item_id) — sort descending
            all_results_sorted = sorted(all_results, key=lambda x: x[1], reverse=True)
            best_db_desc, confidence_score, best_match_key = all_results_sorted[0]
            best_match_id = self._reverse_map[best_match_key]

            if _return_candidates:
                # Return top-5 as (score, id, db_desc) for the debug logger
                # We group by item_id to avoid showing the same item multiple times if both main/alias matched high
                seen_ids = set()
                top5 = []
                for db_desc, score, s_key in all_results_sorted:
                    mid = self._reverse_map[s_key]
                    if mid not in seen_ids:
                        seen_ids.add(mid)
                        top5.append((score, mid, db_desc))
                        if len(top5) == 5:
                            break
                            
                return best_match_id, best_db_desc, confidence_score, candidates, search_target, top5

            return best_match_id, best_db_desc, confidence_score

        if _return_candidates:
            return None, None, 0.0, candidates, search_target, []
        return None, None, 0.0

    def get_color_code(self, score: float) -> str:
        """
        Map a confidence score to a traffic-light colour name.

        Parameters
        ----------
        score : float
            A value in 0–100 as returned by ``match_item``.

        Returns
        -------
        str
            One of ``"green"``, ``"yellow"``, or ``"red"``.
        """
        if score >= self.THRESHOLD_HIGH:
            return "green"
        elif score >= self.THRESHOLD_MID:
            return "yellow"
        return "red"


# ---------------------------------------------------------------------------
# MatchService — High-level orchestrator (the UI's only entry point)
# ---------------------------------------------------------------------------

class MatchService:
    """
    High-level matching orchestrator.

    This is the single class the UI layer should interact with for any
    database-matching operation.  It wraps ``MatchingEngine`` and adds:

    * **Session awareness** — already-confirmed items are never re-matched;
      their stored ``matched_id`` and a perfect confidence of 100 % are honoured.
    * **Routing awareness** — items whose matched DB entry has a routing tag of
      ``"IGNORE"`` are flagged accordingly so the UI can handle them differently.
    * **Color resolution** — all traffic-light colour logic lives here, not in
      the UI render loop.
    * **Batch enrichment** — ``enrich_items()`` processes an entire session list
      in one call, attaching a ``_match`` metadata dict to each item in-place.

    Color hex constants are defined here so that the UI never hard-codes them.

    Attributes
    ----------
    COLOR_HEX : dict[str, str]
        Maps colour name -> hex string for use with tkinter / customtkinter.
    """

    COLOR_HEX: dict[str, str] = {
        "green":  "#00FF00",
        "yellow": "#FFFF00",
        "red":    "#FF0000",
        "gray":   "gray50",
    }

    def __init__(self, catalog: dict, debug_mode: bool = False, log_dir: str = "logs", llm_model: "str | None" = None):
        """
        Parameters
        ----------
        catalog : dict
            The master catalog dict from ``CatalogLoader.load_all_categories()``.
        debug_mode : bool
            When True, Ollama requests/responses are written to a timestamped
            log file in ``log_dir``.  Propagated to the LLM client.
            Also enables the per-item match diagnostic log.
        log_dir : str
            Directory for debug log files (default: ``"logs/"``).
        """
        self._engine     = MatchingEngine(catalog)
        self._catalog    = catalog
        self._debug_mode = debug_mode
        self._log_dir    = log_dir
        
        self._llm: "GeminiClient | LocalLLMClient"
        gemini_key = ConfigManager.get("gemini_api_key")
        if gemini_key:
            self._llm = GeminiClient(api_key=gemini_key, debug_mode=debug_mode, log_dir=log_dir)
        else:
            self._llm = LocalLLMClient(model=llm_model, debug_mode=debug_mode, log_dir=log_dir)
            
        # Create the match logger only when debug is on (avoids empty log files).
        self._match_log: MatchDebugLogger | None = (
            MatchDebugLogger(log_dir) if debug_mode else None
        )

    @property
    def debug_mode(self) -> bool:
        return self._debug_mode

    def check_ollama_ready(self) -> tuple[bool, str]:
        """
        Verify the LLM connection (Ollama or Gemini).
        Returns (True, "OK") or (False, "Error message").
        """
        if isinstance(self._llm, GeminiClient):
            return True, "Connected to Gemini API."
        return self._llm.check_connection()

    # ------------------------------------------------------------------
    # Public batch API
    # ------------------------------------------------------------------

    def enrich_items(
        self,
        line_items: list,
        progress_callback=None,
        status_callback=None,
    ) -> list:
        """
        Attach match metadata to every item in a session list, in-place.

        Runs up to 3 LLM requests concurrently via ThreadPoolExecutor to
        reduce total processing time when batch sizes are large.

        Parameters
        ----------
        line_items : list
            Session line items to enrich.
        progress_callback : callable | None
            ``fn(current: int, total: int)`` — called after each item resolves.
        status_callback : callable | None
            ``fn(msg: str)`` — called with a human-readable status string
            (e.g. ``"Matching 3/15: Shower Bases SM Vasa..."``).  Use this
            to update the UI status bar from the calling thread.
        """
        total   = len(line_items)
        counter = [0]   # items completed
        started = [0]   # items started
        lock    = Lock()

        def _resolve_and_tag(item: dict) -> dict:
            """Resolve one item and return it (used inside thread pool)."""
            with lock:
                started[0] += 1
                n = started[0]
            
            status_prefix = f"[{n}/{total}]"
            item["_match"] = self._resolve(item, status_callback, status_prefix)
            return item

        with ThreadPoolExecutor(max_workers=3) as pool:
            future_map = {pool.submit(_resolve_and_tag, item): item for item in line_items}
            for future in as_completed(future_map):
                try:
                    future.result()  # propagate any worker exception
                except Exception as exc:
                    item = future_map[future]
                    desc = item.get('raw_description', '')[:60]
                    print(f"[MatchService] Worker error for '{desc}': {exc}")
                    item["_match"] = {
                        "match_id": None, "confidence": 0.0,
                        "color_code": "red", "color_hex": self.COLOR_HEX["red"],
                        "is_ignored": False,
                    }
                with lock:
                    counter[0] += 1
                    if progress_callback:
                        progress_callback(counter[0], total)

        if status_callback:
            status_callback(f"✅ Matched {total} items.")

        return line_items


    # ------------------------------------------------------------------
    # Public single-item API
    # ------------------------------------------------------------------

    def resolve_match(self, item: dict) -> dict:
        """
        Return match metadata for a single line item.

        Used by the inspect popup and any other component that needs
        on-demand resolution for one item rather than an entire batch.

        If the item was already processed by ``enrich_items()`` it will carry
        a ``_match`` key — this method returns that cached value immediately
        without touching Ollama.  Only genuinely uncached items fall through
        to the full LLM resolution path.

        Parameters
        ----------
        item : dict
            A single line item dict (may or may not have ``matched_id``).

        Returns
        -------
        dict
            A ``_match`` metadata dict — same shape as produced by
            ``enrich_items`` (see its docstring for the full schema).
        """
        # Fast path — return the result already computed by enrich_items().
        # Prevents Ollama being called again every time the user opens the
        # inspect popup for an item that was already matched in the batch.
        if "_match" in item:
            return item["_match"]

        # Slow fallback — item hasn't been enriched yet.
        return self._resolve(item)


    # ------------------------------------------------------------------
    # Internal helpers — not part of the public contract
    # ------------------------------------------------------------------

    def _resolve(self, item: dict, status_callback=None, status_prefix: str = "") -> dict:
        """
        Core resolution logic shared by ``enrich_items`` and ``resolve_match``.
        """
        confirmed = item.get("confirmed", False)
        contract_item: ContractItem | None = None
        search_target = ""
        candidates_after_filter: dict = {}
        top5: list = []
        fast_path_used = False
        match_id: str | None = None
        confidence: float = 0.0

        short_desc = item.get("raw_description", "")[:50]
        category   = item.get("category", "")
        label      = f"{category}: {short_desc}" if category else short_desc

        if confirmed and "matched_id" in item:
            # User-confirmed — trust the stored decision.
            match_id   = item["matched_id"]
            confidence = 100.0
            if status_callback:
                status_callback(f"✅ {status_prefix} Restored: {label}")
        else:
            raw_desc = item.get("raw_description", "")
            
            # --- 1. FAST PATH ---
            # Try a direct token_set_ratio match to bypass LLM on exact/labor items
            fast_results = self._engine.fast_match(raw_desc)
            if fast_results:
                score1, id1, desc1 = fast_results[0]
                score2, id2, desc2 = fast_results[1] if len(fast_results) > 1 else (0.0, None, "")
                
                # Margin of Victory logic
                is_perfect = (score1 == 100.0)
                is_high_with_margin = (score1 >= 95.0 and (score1 - score2) >= 5.0)
                
                if is_perfect or is_high_with_margin:
                    match_id = id1
                    confidence = score1
                    fast_path_used = True
                    search_target = raw_desc
                    top5 = fast_results  # Log the fast path candidates
                    if status_callback:
                        status_callback(f"⚡ {status_prefix} DB Match (Fast): {label}")
            
            # --- 2. SLOW PATH (LLM Fallback) ---
            if not fast_path_used:
                from models.config_manager import ConfigManager
                role = ConfigManager.get("role") or "user"
                
                # Standard users ONLY use Fast Match to avoid Ollama connection overhead/errors
                if role != "admin":
                    match_id = None
                    confidence = 0.0
                else:
                    # Admins use Ollama, but ONLY if it is actually responding
                    ready, _ = self.check_ollama_ready()
                    if not ready:
                        if status_callback:
                            status_callback(f"⚠️ {status_prefix} Ollama Offline: {label}")
                        match_id = None
                        confidence = 0.0
                    else:
                        if status_callback:
                            service_name = "Gemini" if isinstance(self._llm, GeminiClient) else "Ollama"
                            status_callback(f"🧠 {status_prefix} AI Match ({service_name}): {label}")
                        
                        hint_section  = item.get("section") or None
                        hint_category = item.get("category") or None
                        try:
                            contract_item = self._llm.extract_product_fields(
                                raw_desc,
                                hint_category=hint_category,
                                hint_section=hint_section,
                            )
                            if self._debug_mode:
                                # Use the extended return value to capture candidates + ranking
                                result = self._engine.match_item(contract_item, _return_candidates=True)
                                match_id, _, confidence, candidates_after_filter, search_target, top5 = result
                            else:
                                match_id, _, confidence = self._engine.match_item(contract_item)
                        except Exception as e:
                            print(f"[MatchService] LLM error for '{raw_desc[:60]}': {e}")
                            match_id   = None
                            confidence = 0.0

        # Routing tag check
        is_ignored = False
        if match_id and match_id in self._catalog:
            routing    = self._catalog[match_id].get("routing_tag", "").strip().upper()
            is_ignored = (routing == "IGNORE")

        # Traffic-light colour
        if confirmed:
            color_code = "gray" if is_ignored else "green"
        else:
            color_code = self._engine.get_color_code(confidence)
            if is_ignored:
                if color_code == "red":
                    # Do not allow low-confidence matches to silently ignore themselves
                    is_ignored = False
                else:
                    color_code = "gray"

        # Write match diagnostic log if debug is on
        if self._match_log is not None:
            self._match_log.log_resolution(
                item=item,
                contract_item=contract_item,
                search_target=search_target,
                catalog_size=len(self._engine._index),
                candidates_after_filter=candidates_after_filter,
                top_results=top5,
                final_id=match_id,
                confidence=confidence,
                color_code=color_code,
                confirmed=confirmed,
                is_ignored=is_ignored,
                fast_path_used=fast_path_used,
            )

        return {
            "match_id":   match_id,
            "confidence": confidence,
            "color_code": color_code,
            "color_hex":  self.COLOR_HEX.get(color_code, "gray50"),
            "is_ignored": is_ignored,
            "fast_path_used": fast_path_used,
            "extracted_fields": contract_item.model_dump() if contract_item else None,
        }
