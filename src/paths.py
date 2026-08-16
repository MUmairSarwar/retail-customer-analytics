from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

RAW_XLSX = RAW_DIR / "Online Retail.xlsx"
DATABASE = PROCESSED_DIR / "retail.db"


def ensure_directories() -> None:
    for path in (RAW_DIR, PROCESSED_DIR, REPORTS_DIR, FIGURES_DIR):
        path.mkdir(parents=True, exist_ok=True)

