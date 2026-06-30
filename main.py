from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parent / "src"
if SRC_DIR.exists():
    sys.path.insert(0, str(SRC_DIR))

from candidate_transformer.cli.main import main


if __name__ == "__main__":
    raise SystemExit(main())
