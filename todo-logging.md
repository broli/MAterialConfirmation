# Logging Future Tasks (TBD)

This document tracks ideas and pending tasks for improving the application's developer debug logging. These logs will only be written when the "Enable Developer Logging" toggle is active.

## Generators
- [ ] **PDF Generator Logging**: Implement a `DebugLogger` in `models/client_pdf_generator.py` to trace the PDF creation process. Log what is intended (e.g., "Generating PDF for client X with Y items") and the results of calculations (e.g., image dimensions, layout calculations, pagination boundaries).
- [ ] **Excel Generator Logging**: Implement a `DebugLogger` in `models/excel_routing_engine.py` to trace Excel file creation. Log the template loading, sheet duplication/renaming per room, insertion row calculations, and routing tags assigned to items.

## App State & UI interactions
- [ ] **App Controller Flow**: Log general UI interactions such as button clicks, session saves, unconfirming items, and state transitions to a central `app_controller.log`.

## Models & Database
- [ ] **Catalog & Database Loader Logging**: Log the number of products loaded, any skipped corrupted entries, or schema validation failures when `CatalogLoader` parses the database.
- [ ] **Settings/Config Loading**: Log if missing config keys are defaulted, or if a corrupted `config.yaml` is recovered.
- [ ] **Session State Recovery**: When loading a saved `.json` session, log how many items were recovered and their matching statuses.
