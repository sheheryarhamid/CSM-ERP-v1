"""Simple scaffold for new modules (filesystem only)
Usage: python -m module_sdk.create_module --name "My Module" --id com.example.my --out ./modules/my
"""

import argparse
import json
from pathlib import Path

MANIFEST_TEMPLATE = {
    "name": "My Module",
    "id": "com.example.my",
    "version": "0.1.0",
    "api_version": "v1",
    "capabilities": [],
    "permissions": [],
    "db_requirements": [],
    "dependencies": [],
    "signed_by": None,
    "upgrade_path": None,
}

README = """# Module: {name}

This is a scaffolded module. Fill in implementation and manifest.
"""


def scaffold(name: str, id_: str, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    manifest = MANIFEST_TEMPLATE.copy()
    manifest["name"] = name
    manifest["id"] = id_
    with open(out / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    with open(out / "README.md", "w", encoding="utf-8") as f:
        f.write(README.format(name=name))
    (out / "src").mkdir(exist_ok=True)
    with open(out / "src" / "__init__.py", "w", encoding="utf-8") as f:
        f.write("# module code")
    print(f"Scaffolded module at {out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--name", required=True)
    p.add_argument("--id", required=True)
    p.add_argument("--out", default="./modules/new_module")
    args = p.parse_args()
    scaffold(args.name, args.id, Path(args.out))
