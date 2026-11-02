"""Single source of truth for local data paths. No raw data is committed."""
from pathlib import Path
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data_source"
RAW = DATA / "raw"
INTERMEDIATE = DATA / "intermediate"
QUALITY = DATA / "processed" / "03_quality_results"
COLLISION = DATA / "processed" / "05_collision_results"
MAPS = DATA / "output" / "04_map_results"

def ensure_output_dirs():
    for directory in (INTERMEDIATE, QUALITY, COLLISION, MAPS):
        directory.mkdir(parents=True, exist_ok=True)
