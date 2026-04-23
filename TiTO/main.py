import sys
from pathlib import Path

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root / "src"))

from tito.__main__ import main

if __name__ == "__main__":
    main()
