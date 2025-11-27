import sys
from pathlib import Path

p=Path(sys.argv[1])
text=p.read_text(encoding='utf-8').splitlines()
for i,l in enumerate(text, start=1):
    print(f"{i:4}: {l}")
