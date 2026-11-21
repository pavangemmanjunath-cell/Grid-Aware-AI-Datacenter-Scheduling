import csv
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
sys.path.insert(0, str(REPO / "scripts"))


@pytest.fixture(scope="session")
def bench() -> pd.DataFrame:
    return pd.read_csv(DATA / "research_benchmark_168h.csv")


@pytest.fixture(scope="session")
def jobs() -> pd.DataFrame:
    return pd.read_csv(DATA / "research_flexible_jobs.csv")


@pytest.fixture(scope="session")
def results() -> dict:
    with open(DATA / "research_results_gridflex.csv", newline="") as fh:
        return {row["scenario"].split()[0]: {k: (v if k == "scenario" else float(v)) for k, v in row.items()}
                for row in csv.DictReader(fh)}


@pytest.fixture(scope="session")
def summary() -> dict:
    return json.loads((DATA / "verification_summary.json").read_text())


@pytest.fixture(scope="session")
def reference_model():
    """Full Python/SciPy reference run (about 20-60 s). Shared by integration tests."""
    from qh2dc_reference import run_reference_model
    return run_reference_model()
