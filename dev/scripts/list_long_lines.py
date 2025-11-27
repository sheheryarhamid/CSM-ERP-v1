import sys
from pathlib import Path


def list_long(path, limit=100):
    p = Path(path)
    if not p.exists():
        print(f"File not found: {path}")
        return
    for i, l in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        if len(l) > limit:
            print(f"{path}:{i}:{len(l)}: {l}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: list_long_lines.py <file> [limit]")
        sys.exit(2)
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    list_long(sys.argv[1], limit)
