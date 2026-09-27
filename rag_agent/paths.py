from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
SOURCES_CSV = DATA_DIR / "sources.csv"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
