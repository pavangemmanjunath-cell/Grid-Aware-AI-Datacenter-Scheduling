# Release guide

## Before release

- [ ] `python -m pytest` passes (root) and `python -m pytest` passes in `webapp/backend`
- [ ] `npm ci && npm run build` passes in `webapp/frontend`
- [ ] CI green on the release commit
- [ ] `python scripts/export_static_snapshot.py` re-run if anything in `data/` or the engine changed
- [ ] documentation updated (README, docs/, webapp/README.md)
- [ ] `CHANGELOG.md` updated; version bumped consistently in `CITATION.cff`, `webapp/backend/app/config.py`,
      `webapp/backend/pyproject.toml`, `webapp/frontend/package.json`
- [ ] `CITATION.cff` valid (`cffconvert --validate`, run in CI)
- [ ] secrets scan clean (no `.env`, keys or tokens; check `git log -p` for history)
- [ ] licence and third-party notices correct
- [ ] examples execute; links verified

## Versioning

Semantic versioning `MAJOR.MINOR.PATCH`, tags with a lowercase `v`: `v1.0.0`, `v1.1.0`, `v1.1.1`, `v2.0.0`.

- **MAJOR** — backward-incompatible changes (e.g. API v2, changed data schema).
- **MINOR** — new backward-compatible capability (e.g. a baseline scheduler, a new endpoint).
- **PATCH** — backward-compatible fixes and documentation corrections.

Avoid tags such as `V_1.1`, `Version_1` or `release_new`.

## GitHub release

```bash
git switch main && git pull
git tag -a v1.0.0 -m "QH2DC v1.0.0"
git push origin v1.0.0
```

Then *Releases → Draft a new release*, choose the tag, paste the notes from `docs/releases/vX.Y.Z.md`, publish.

## Zenodo

With the repository enabled in Zenodo (Zenodo → GitHub → toggle the repository):

GitHub release → Zenodo ingests it → archived software version → version DOI (plus a concept DOI for all
versions). Zenodo reads `CITATION.cff`; this repository deliberately has no `.zenodo.json`, because
Zenodo would prefer it over `CITATION.cff`. Do not upload the same release manually.

## Post-release

1. Verify the Zenodo record (title, authors, ORCID, licence, version).
2. Add the DOI badge and the software DOI to `README.md`:
   `[![DOI](https://zenodo.org/badge/DOI/<DOI>.svg)](https://doi.org/<DOI>)`
3. Add `doi:` / `identifiers:` to `CITATION.cff` for the next release.
4. Record the release in `CHANGELOG.md`.

Never rewrite archived history to make it look cleaner; ship a new version instead. Keep the **software
DOI** (Zenodo) and the **paper DOI** (Elsevier) separate.
