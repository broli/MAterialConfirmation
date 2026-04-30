"""
db_migrate.py
=============
One-time database migration script.

Changes applied to every YAML file in database/categories/:

  1. REMOVE  `matching_rules`          — legacy regex block, not used by the
                                         current deterministic + LLM pipeline.
                                         (must_contain_regex, must_not_contain_regex,
                                          keywords sub-keys all go away)

  2. CLEAN   `provider`                — "MISSING_PROVIDER" sentinel → "" (empty).
                                         The UI treats blank as "not set"; the old
                                         sentinel clutters inspectors and reports.

  3. ENSURE  `purchase_link`           — add empty string if key is absent.

  4. CANONICAL field order             — rewrite each item in the canonical schema
                                         order so all YAMLs are consistently formatted:

         id, sku, brand, provider, routing_tag,
         purchase_link, oneclick_description, printable

A timestamped backup of the entire categories/ directory is saved to
database/categories_backup_YYYYMMDD_HHMMSS/ before any changes are written.

Run once with:
    python db_migrate.py

Run in dry-run mode (no writes) with:
    python db_migrate.py --dry-run
"""

import os
import sys
import shutil
import yaml
from datetime import datetime

# ─── Config ──────────────────────────────────────────────────────────────────
CAT_DIR     = "database/categories"
BACKUP_ROOT = "database"
DRY_RUN     = "--dry-run" in sys.argv

# Canonical field order for each item (unknown keys appended at end)
FIELD_ORDER = [
    "id", "sku", "brand", "provider", "routing_tag",
    "purchase_link", "oneclick_description", "printable",
]

# ─── Backup ───────────────────────────────────────────────────────────────────
def make_backup() -> str:
    stamp      = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(BACKUP_ROOT, f"categories_backup_{stamp}")
    shutil.copytree(CAT_DIR, backup_dir)
    return backup_dir


# ─── Single-item migration ─────────────────────────────────────────────────────
def migrate_item(item: dict) -> tuple[dict, list[str]]:
    """
    Return (migrated_item, list_of_changes) for one catalog entry.
    Changes is a list of human-readable strings describing what was altered.
    """
    changes = []
    out     = {}

    # 1. Remove matching_rules
    if "matching_rules" in item:
        changes.append("removed matching_rules")

    # 2. Clean MISSING_PROVIDER
    provider = item.get("provider", "")
    if isinstance(provider, str) and provider.strip().upper() == "MISSING_PROVIDER":
        provider = ""
        changes.append("cleared provider (was MISSING_PROVIDER)")

    # 3. Ensure purchase_link exists
    purchase_link = item.get("purchase_link", "")
    if "purchase_link" not in item:
        changes.append("added purchase_link (empty)")

    # 4. Rebuild in canonical order
    merged = {**item}   # shallow copy
    merged.pop("matching_rules", None)
    merged["provider"]      = provider
    merged["purchase_link"] = purchase_link

    for key in FIELD_ORDER:
        if key in merged:
            out[key] = merged.pop(key)

    # Append any unexpected extra keys at the end (forward-compat)
    for key, val in merged.items():
        out[key] = val
        changes.append(f"preserved unknown key '{key}'")

    return out, changes


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    if not os.path.isdir(CAT_DIR):
        print(f"ERROR: '{CAT_DIR}' not found. Run from the project root.")
        sys.exit(1)

    yaml_files = [f for f in os.listdir(CAT_DIR) if f.endswith(".yaml")]
    if not yaml_files:
        print("No YAML files found.")
        sys.exit(0)

    mode_label = "DRY-RUN - no files will be written" if DRY_RUN else "LIVE"
    print(f"\n{'='*60}")
    print(f"  DB Migration  [{mode_label}]")
    print(f"  Files : {len(yaml_files)}")
    print(f"{'='*60}\n")

    # Backup (only in live mode)
    if not DRY_RUN:
        backup_dir = make_backup()
        print(f"[OK] Backup saved -> {backup_dir}\n")

    total_items   = 0
    total_changes = 0

    for fname in sorted(yaml_files):
        fpath = os.path.join(CAT_DIR, fname)
        with open(fpath, encoding="utf-8") as f:
            items = yaml.safe_load(f) or []

        migrated = []
        file_changes = 0

        for item in items:
            new_item, changes = migrate_item(item)
            migrated.append(new_item)
            total_items += 1
            if changes:
                file_changes += len(changes)
                total_changes += len(changes)
                iid = item.get("id", "?")
                for c in changes:
                    print(f"  [{fname}] {iid}: {c}")

        if not DRY_RUN:
            with open(fpath, "w", encoding="utf-8") as f:
                yaml.dump(migrated, f, sort_keys=False, allow_unicode=True)

        status = f"  -> {file_changes} changes" if file_changes else "  -> no changes"
        print(f"{'[DRY]' if DRY_RUN else '    '} {fname:<30} {len(items):3d} items{status}\n")

    print(f"{'='*60}")
    print(f"  Total items  : {total_items}")
    print(f"  Total changes: {total_changes}")
    if DRY_RUN:
        print("  (Dry-run: nothing written.  Re-run without --dry-run to apply.)")
    else:
        print("  [OK] Migration complete.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
