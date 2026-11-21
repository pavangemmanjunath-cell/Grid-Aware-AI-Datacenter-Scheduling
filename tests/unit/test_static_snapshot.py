"""The web app's committed offline snapshot must match the published data files.

If this fails after a change in data/, regenerate it with
``python scripts/export_static_snapshot.py``.
"""
import hashlib
import json

import pytest

from conftest import DATA, REPO

SNAPSHOT = REPO / "webapp" / "frontend" / "public" / "data" / "qh2dc.json"


@pytest.fixture(scope="module")
def snap():
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def test_snapshot_hashes_match_data_files(snap):
    for name, digest in snap["meta"]["sourceSha256"].items():
        assert hashlib.sha256((DATA / name).read_bytes()).hexdigest() == digest, name


def test_snapshot_table_is_the_published_table(snap, results):
    for row in snap["table"]:
        pub = results[row["scenario"].split()[0]]
        for k, v in row.items():
            if k != "scenario":
                assert v == pytest.approx(pub[k], rel=1e-12), (row["scenario"], k)


def test_snapshot_schedules_respect_envelopes(snap, results):
    for key, sc in snap["scenarios"].items():
        if key == "R2_unconstrained" or sc["cap"] is None:
            continue
        for g, c in zip(sc["series"]["grid"], sc["cap"]):
            assert g <= c + 1e-3, key


def test_snapshot_dataset_catalogue_matches(snap):
    assert snap["datasets"] == json.loads((DATA / "public_datasets.json").read_text(encoding="utf-8"))
