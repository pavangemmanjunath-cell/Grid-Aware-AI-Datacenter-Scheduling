"""Run the independent Python/SciPy reference model without touching tracked files.

``verify/verify_python.py`` is a script, not a library: when executed it solves every
scenario, rebuilds the QUBO, replays the QAOA angles, and then *writes* into
``data/`` and ``figures/`` next to itself.  Running it in place would overwrite the
published artefacts in this repository.

This helper copies the script and the two input CSV files into a temporary
workspace with the same ``verify/ data/ figures/`` layout, executes it there with
``runpy``, and hands back the script's global namespace so callers can read the
solved schedules (``res``), the QAOA results (``qaoa_res``) and so on.  The
original files are only read, never modified.

Used by ``scripts/crosscheck.py``, ``scripts/export_static_snapshot.py`` and
``tests/integration``.
"""
from __future__ import annotations

import contextlib
import io
import runpy
import shutil
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INPUT_CSVS = ("research_benchmark_168h.csv",)


def run_reference_model(workdir: Path | None = None, quiet: bool = True) -> dict:
    """Execute ``verify/verify_python.py`` in an isolated copy and return its globals.

    Parameters
    ----------
    workdir:
        Directory to run in.  A fresh temporary directory is used when omitted and
        removed afterwards; pass a path to keep the regenerated figures and JSON.
    quiet:
        Suppress the script's own console table.
    """
    owns_tmp = workdir is None
    root = Path(tempfile.mkdtemp(prefix="qh2dc_")) if owns_tmp else Path(workdir)
    try:
        (root / "verify").mkdir(parents=True, exist_ok=True)
        (root / "data").mkdir(exist_ok=True)
        (root / "figures").mkdir(exist_ok=True)
        shutil.copy2(REPO / "verify" / "verify_python.py", root / "verify" / "verify_python.py")
        for name in INPUT_CSVS:
            shutil.copy2(REPO / "data" / name, root / "data" / name)

        sink = io.StringIO()
        ctx = contextlib.redirect_stdout(sink) if quiet else contextlib.nullcontext()
        with ctx:
            g = runpy.run_path(str(root / "verify" / "verify_python.py"), run_name="__qh2dc_reference__")
        g["_workdir"] = root
        g["_stdout"] = sink.getvalue()
        return g
    finally:
        if owns_tmp:
            shutil.rmtree(root, ignore_errors=True)
