"""
etl_pipeline.py - Master ETL script (Extract -> Transform -> Load -> Verify).

Runs the whole data-engineering layer with no manual steps:
  1. Extract : locate the 10 source datasets (data/raw or a folder you pass)
  2. Transform: clean every dataset (scripts/clean_data.py)
  3. Load     : build the SQLite star schema and load it (scripts/load_db.py)
  4. Verify   : row counts vs CSVs and foreign-key check (inside load_db.py)

Usage (from the project root):
    python scripts/etl_pipeline.py
    python scripts/etl_pipeline.py "C:\\path\\to\\csv_folder"

Every step is logged to logs/etl.log; the script exits with a non-zero code if any step fails.
"""
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import clean_data   # noqa: E402
import load_db      # noqa: E402

LOG_FILE = ROOT / "logs" / "etl.log"


def setup_logging():
    LOG_FILE.parent.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s",
        handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()], force=True)


def check_sources(extra=None):
    """Extract step: make sure all 10 datasets can be found before doing any work."""
    missing = [n for n in clean_data.NAMES if clean_data.find_file(n, extra) is None]
    if missing:
        raise FileNotFoundError(f"Missing source datasets: {', '.join(missing)}. Put them in data/raw/ or pass the folder.")
    logging.info("Extract: all %d source datasets found", len(clean_data.NAMES))


def run(extra=None) -> int:
    setup_logging()
    t0 = time.time()
    try:
        logging.info("ETL started")
        check_sources(extra)
        logging.info("Transform: cleaning datasets")
        clean_data.main(extra)
        logging.info("Load: building SQLite database")
        rc = load_db.main()
        if rc != 0:
            raise RuntimeError("Database verification failed (row counts or foreign keys)")
        logging.info("ETL finished OK in %.1f s", time.time() - t0)
        return 0
    except Exception as exc:                      # log every failure, never fail silently
        logging.error("ETL FAILED: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(run(sys.argv[1] if len(sys.argv) > 1 else None))
