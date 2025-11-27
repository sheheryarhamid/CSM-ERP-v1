import json
import sys
from pathlib import Path

from jsonschema import ValidationError, validate

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "docs" / "manifests" / "manifest-schema.json"

def load_schema():
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_manifest(manifest_path: str) -> bool:
    schema = load_schema()
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.loads(f.read())
    try:
        validate(instance=manifest, schema=schema)
        print("Manifest is valid")
        return True
    except ValidationError as e:
        print("Manifest validation failed:")
        print(e)
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python -m module_sdk.validator path/to/manifest.json")
        sys.exit(2)
    ok = validate_manifest(sys.argv[1])
    sys.exit(0 if ok else 1)
