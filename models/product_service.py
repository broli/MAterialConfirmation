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
    def upsert_to_yaml(product: dict, cat_file: str, categories_path: str, assets_path: str = None) -> None:
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
        assets_path : str
            Absolute path to the ``database/assets/`` directory (used for copying images).
        """
        # Handle absolute paths for images
        if assets_path and "printable" in product:
            img = product["printable"].get("image_file", "")
            if img and os.path.isabs(img) and os.path.exists(img):
                new_img = ProductService.copy_image_to_assets(img, assets_path)
                product["printable"]["image_file"] = new_img

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

    # Old tkinter dimension helpers removed for PySide6 transition.
