"""
run_pipeline.py - master run script: runs the whole project end to end with one command.

    python run_pipeline.py                      # source CSVs in data/raw
    python run_pipeline.py "C:\\path\\to\\csvs"   # source CSVs elsewhere

Steps: ETL (clean + load SQLite) -> performance metrics -> dashboard data -> SQL queries -> data dictionary.
Stops at the first step that fails. Notebooks in notebooks/ read the files this script writes.
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
S = ROOT / "scripts"
extra = [sys.argv[1]] if len(sys.argv) > 1 else []
STEPS = [("ETL: clean data and load SQLite", [S / "etl_pipeline.py", *extra]),
         ("Compute performance and risk metrics", [S / "compute_metrics.py"]),
         ("Prepare dashboard data", [S / "export_dashboard_data.py"]),
         ("Run the 10 SQL queries", [S / "run_queries.py"]),
         ("Regenerate the data dictionary", [S / "make_dictionary.py"])]

t0 = time.time()
for i, (title, cmd) in enumerate(STEPS, 1):
    print(f"\n[{i}/{len(STEPS)}] {title}")
    if subprocess.run([sys.executable, *map(str, cmd)], cwd=ROOT).returncode != 0:
        sys.exit(f"\nPipeline stopped: step {i} failed ({title}). See the messages above and logs/etl.log.")
print(f"\nPipeline finished OK in {time.time() - t0:.0f} s")
