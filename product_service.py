"""
product_service.py
==================
Shared, stateless service for all YAML-based product CRUD operations.

This module eliminates the duplicated save/delete/image-copy logic that
previously existed separately in database_manager.py and batch_pdf_ui.py.

All methods are @staticmethods — no instantiation required:

    from product_service import ProductService

    ProductService.upsert_to_yaml(product, "faucets.yaml", categories_path)
    ProductService.delete_from_yaml("my-faucet-id", "faucets.yaml", categories_path)
    filename = ProductService.copy_image_to_assets(source_path, assets_path)
    rows = ProductService.build_dimension_rows(parent_frame, existing_dims)
    dims = ProductService.read_dimension_rows(rows)
"""

import os
import shutil
import yaml
import customtkinter as ctk


class ProductService:
    """
    Stateless utility class for product CRUD and UI helpers.
    All methods are static — never instantiate this class.
    """

    # ─────────────────────────────────────────────────────────────────────────
    # YAML persistence
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def upsert_to_yaml(product: dict, cat_file: str, categories_path: str) -> None:
        """
        Write (or overwrite) a product into the given category YAML file.

        If a product with the same ``id`` already exists in the file it is
        replaced in-place; otherwise the product is appended.  The file is
        created if it does not yet exist.

        Parameters
        ----------
        product : dict
            The full product dictionary to persist.
        cat_file : str
            The YAML filename (e.g. ``"faucets.yaml"``).  Extension is
            auto-appended if missing.
        categories_path : str
            Absolute path to the ``database/categories/`` directory.
        """
        if not cat_file.endswith(".yaml"):
            cat_file += ".yaml"

        target = os.path.join(categories_path, cat_file)
        existing: list = []
        if os.path.exists(target):
            with open(target, "r", encoding="utf-8") as f:
                existing = yaml.safe_load(f) or []

        # Replace if ID already present, otherwise append
        existing = [i for i in existing if i.get("id") != product.get("id")]
        existing.append(product)

        with open(target, "w", encoding="utf-8") as f:
            yaml.dump(existing, f, sort_keys=False, allow_unicode=True)

    @staticmethod
    def remove_from_yaml(item_id: str, cat_file: str, categories_path: str) -> None:
        """
        Remove the product with ``item_id`` from the given YAML file.

        Does nothing if the file does not exist or the ID is not found.

        Parameters
        ----------
        item_id : str
            The ``id`` field of the product to remove.
        cat_file : str
            The YAML filename (e.g. ``"faucets.yaml"``).
        categories_path : str
            Absolute path to the ``database/categories/`` directory.
        """
        if not cat_file.endswith(".yaml"):
            cat_file += ".yaml"

        target = os.path.join(categories_path, cat_file)
        if not os.path.exists(target):
            return

        with open(target, "r", encoding="utf-8") as f:
            existing = yaml.safe_load(f) or []

        updated = [i for i in existing if i.get("id") != item_id]

        with open(target, "w", encoding="utf-8") as f:
            yaml.dump(updated, f, sort_keys=False, allow_unicode=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Asset management
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def copy_image_to_assets(source_path: str, assets_path: str) -> str:
        """
        Copy an image file into the assets directory (if not already there).

        Parameters
        ----------
        source_path : str
            Absolute path of the source image.
        assets_path : str
            Absolute path to the ``database/assets/`` directory.

        Returns
        -------
        str
            The basename of the image file (for storage in the YAML).
        """
        filename = os.path.basename(source_path)
        dest = os.path.join(assets_path, filename)
        if os.path.abspath(source_path) != os.path.abspath(dest):
            shutil.copy(source_path, dest)
        return filename

    # ─────────────────────────────────────────────────────────────────────────
    # Dimension row UI helpers
    # ─────────────────────────────────────────────────────────────────────────

    _DIM_OPTIONS = ["Width", "Length", "Height", "Depth", "Thickness", "Diameter", "Size"]

    @staticmethod
    def build_dimension_rows(
        parent_frame: ctk.CTkFrame,
        existing_dims: dict | None = None,
        row_store: list | None = None,
    ) -> list:
        """
        Dynamically render dimension input rows inside *parent_frame*.

        Each row consists of a read-only ComboBox (measurement type) and a
        free-text Entry (value + unit).  A red "X" button removes the row.

        Parameters
        ----------
        parent_frame : ctk.CTkFrame
            The frame to pack rows into.
        existing_dims : dict | None
            Pre-populate rows from an existing ``dimensions`` dict.
            Pass ``None`` or ``{}`` to start with no rows.
        row_store : list | None
            An existing list to append ``(combo, entry)`` tuples to.
            If ``None``, a new list is created and returned.

        Returns
        -------
        list
            List of ``(combo_widget, entry_widget)`` tuples for later reading.
        """
        if row_store is None:
            row_store = []

        items = existing_dims.items() if existing_dims else []

        def _add_row(key: str = "", value: str = "") -> None:
            options = list(ProductService._DIM_OPTIONS)
            if key and key not in options:
                options.append(key)

            row_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2, padx=5)

            combo = ctk.CTkComboBox(row_frame, values=options, width=120, state="readonly")
            combo.set(key if key else options[0])
            combo.pack(side="left", padx=5)

            entry = ctk.CTkEntry(row_frame, placeholder_text='e.g. 60" or 3 sqft', width=150)
            if value:
                entry.insert(0, str(value))
            entry.pack(side="left", padx=5, expand=True, fill="x")

            def _remove(c=combo, f=row_frame):
                f.destroy()
                nonlocal row_store
                row_store[:] = [r for r in row_store if r[0] is not c]

            ctk.CTkButton(
                row_frame, text="X", width=30,
                fg_color="red", hover_color="darkred",
                command=_remove,
            ).pack(side="right", padx=5)

            row_store.append((combo, entry))

        for k, v in items:
            _add_row(k, str(v) if v else "")

        # Expose the _add_row helper on the frame so callers can wire the
        # "+ Add Measurement" button without duplicating the logic.
        parent_frame._add_dimension_row = _add_row  # type: ignore[attr-defined]
        return row_store

    @staticmethod
    def read_dimension_rows(row_store: list) -> dict:
        """
        Collect current values from a list of ``(combo, entry)`` tuples.

        Parameters
        ----------
        row_store : list
            List of ``(combo_widget, entry_widget)`` tuples as returned by
            ``build_dimension_rows``.

        Returns
        -------
        dict
            ``{ "Width": "60\"", "Depth": "18\"", ... }`` — empty pairs skipped.
        """
        dims: dict = {}
        for combo, entry in row_store:
            k = combo.get().strip()
            v = entry.get().strip()
            if k and v:
                dims[k] = v
        return dims
