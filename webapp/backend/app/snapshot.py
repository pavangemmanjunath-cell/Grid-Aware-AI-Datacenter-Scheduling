"""Write the exact responses of the read-only research API to static JSON files.

The dashboard reads the live API when it is running and these files otherwise (e.g. on GitHub Pages),
so both modes show byte-identical data.  The published data files are copied alongside for download.
Component files are written for hour 0; their hour-independent fields (series, totals, peaks, limits) are
what the dashboard reads - it derives the value at any hour from ``series[hour]``.

    cd webapp/backend
    python -m app.snapshot            # -> webapp/frontend/public/api-snapshot/ and public/data/
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from .api.research import DOWNLOADS, NODES, SCENARIOS
from .config import get_settings
from .main import create_app

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "public"


def main() -> int:
    out = FRONTEND / "api-snapshot"
    if out.exists():
        shutil.rmtree(out)
    (out / "components").mkdir(parents=True)
    with TestClient(create_app()) as c:
        def save(path: str, name: str) -> None:
            r = c.get(path)
            r.raise_for_status()
            (out / name).write_text(json.dumps(r.json(), separators=(",", ":")), encoding="utf-8")

        for ep in ("meta", "scenarios", "benchmark", "qaoa", "components"):
            save(f"/api/{ep}", f"{ep}.json")
        for s in SCENARIOS:
            save(f"/api/dispatch?scenario={s}", f"dispatch_{s}.json")
            save(f"/api/jobs?scenario={s}", f"jobs_{s}.json")
            for node_id, *_ in NODES:
                save(f"/api/components/{node_id}?scenario={s}&hour=0", f"components/{node_id}_{s}.json")
    data = get_settings().data_dir
    dl = FRONTEND / "data"
    dl.mkdir(exist_ok=True)
    for name, rel in DOWNLOADS.items():
        shutil.copy2(data / rel, dl / name)
    n = sum(1 for _ in out.rglob("*.json"))
    print(f"wrote {n} snapshot files to {out} and {len(DOWNLOADS)} downloads to {dl}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
