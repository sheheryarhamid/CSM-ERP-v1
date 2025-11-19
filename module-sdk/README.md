Module SDK (Python)

Purpose: Provide helpers for module authors: manifest generation, validation, message bus helper, and a small CLI to scaffold modules.

Usage:
- Validate a manifest:
  `python -m module_sdk.validator path/to/manifest.yaml`

- Scaffold a new module:
  `python -m module_sdk.create_module --name "My Module" --id com.example.my --out ./modules/my` 
