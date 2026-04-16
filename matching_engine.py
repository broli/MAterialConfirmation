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

from rapidfuzz import process, fuzz


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

        # { item_id -> oneclick_description } — pre-built for fast repeated lookups.
        self._index: dict[str, str] = {}

        for item_id, item_data in catalog.items():
            desc = item_data.get("oneclick_description", "").strip()
            # oneclick_description is mandatory per schema.  If missing, add a
            # visible sentinel so the item surfaces clearly during data-quality review.
            self._index[item_id] = desc if desc else "TBD_UPDATE_ME"

    # ------------------------------------------------------------------
    # Public search API
    # ------------------------------------------------------------------

    def match_item(self, extracted_text: str) -> tuple:
        """
        Find the single best catalog entry for a raw text string.

        Uses ``rapidfuzz.WRatio`` which handles description length mismatch
        gracefully — important because PDFs often include verbose surrounding text.

        Parameters
        ----------
        extracted_text : str
            Raw text extracted from a contract/estimate PDF line item.

        Returns
        -------
        tuple[str | None, str | None, float]
            ``(best_match_id, best_match_string, confidence_score)``
            where *confidence_score* is in the range 0–100.
            Returns ``(None, None, 0.0)`` when the index is empty.
        """
        if not self._index:
            return None, None, 0.0

        result = process.extractOne(
            extracted_text,
            self._index,
            scorer=fuzz.WRatio,
        )

        if result:
            best_match_string, confidence_score, best_match_id = result
            return best_match_id, best_match_string, confidence_score

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

    def __init__(self, catalog: dict):
        """
        Parameters
        ----------
        catalog : dict
            The master catalog dict from ``CatalogLoader.load_all_categories()``.
        """
        self._engine  = MatchingEngine(catalog)
        self._catalog = catalog

    # ------------------------------------------------------------------
    # Public batch API
    # ------------------------------------------------------------------

    def enrich_items(self, line_items: list) -> list:
        """
        Attach match metadata to every item in a session list, in-place.

        The metadata is stored under the ``_match`` key of each item dict so
        it can co-exist with the on-disk session fields without polluting them.

        Confirmed items skip the fuzzy engine — their stored ``matched_id``
        is used directly with a confidence of 100 %.

        Parameters
        ----------
        line_items : list[dict]
            The ``line_items`` list from ``session_data`` as produced by
            ``OneClickIngestor.extract_data()``.

        Returns
        -------
        list[dict]
            The same list, each item updated with a ``_match`` dict.

        Notes
        -----
        ``_match`` shape::

            {
                "match_id":   str | None,   # Catalog item ID of the best match
                "confidence": float,         # 0–100
                "color_code": str,           # "green" | "yellow" | "red" | "gray"
                "color_hex":  str,           # Hex string for tkinter text_color
                "is_ignored": bool,          # True if routing_tag == "IGNORE"
            }
        """
        for item in line_items:
            item["_match"] = self._resolve(item)
        return line_items

    # ------------------------------------------------------------------
    # Public single-item API
    # ------------------------------------------------------------------

    def resolve_match(self, item: dict) -> dict:
        """
        Return match metadata for a single line item.

        Used by the inspect popup and any other component that needs
        on-demand resolution for one item rather than an entire batch.

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
        return self._resolve(item)

    # ------------------------------------------------------------------
    # Internal helpers — not part of the public contract
    # ------------------------------------------------------------------

    def _resolve(self, item: dict) -> dict:
        """
        Core resolution logic shared by ``enrich_items`` and ``resolve_match``.

        Determines the best match ID and all associated display metadata for a
        single line item, handling the confirmed/unconfirmed and ignored/normal
        branches.

        Parameters
        ----------
        item : dict
            A single line item dict.

        Returns
        -------
        dict
            Populated ``_match`` metadata dict.
        """
        confirmed = item.get("confirmed", False)

        if confirmed and "matched_id" in item:
            # The user has already reviewed and approved this match.
            # Trust the stored decision — no need to run the fuzzy engine again.
            match_id   = item["matched_id"]
            confidence = 100.0
        else:
            # No confirmed decision yet — run the fuzzy engine.
            raw_desc = item.get("raw_description", "")
            match_id, _, confidence = self._engine.match_item(raw_desc)

        # Check if the matched item is an administrative "IGNORE" routing entry.
        is_ignored = False
        if match_id and match_id in self._catalog:
            routing    = self._catalog[match_id].get("routing_tag", "").strip().upper()
            is_ignored = (routing == "IGNORE")

        # Determine the traffic-light colour.
        if is_ignored:
            color_code = "gray"
        elif confirmed:
            color_code = "green"
        else:
            color_code = self._engine.get_color_code(confidence)

        return {
            "match_id":   match_id,
            "confidence": confidence,
            "color_code": color_code,
            "color_hex":  self.COLOR_HEX.get(color_code, "gray50"),
            "is_ignored": is_ignored,
        }
