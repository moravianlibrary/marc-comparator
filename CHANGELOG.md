# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Kramerius link discovery proposed links to unrelated documents.** Identifiers were
  OR-ed into one query and every hit became a proposed 856, so a single unreliable
  identifier invented dozens of links per record. MZK's Kramerius has ČNB numbers shared
  by unrelated documents — `cnb002657972` matches 41, `cnb002860278` matches 210 — which
  is what produced the bad Aleph batch of July 2026. Hits are now attributed back to the
  identifier that matched them, and an identifier resolving to more than
  `max_documents_per_identifier` (default 1) documents has its hits withheld from the
  repair batch. Verified against the live index: the two reported records go from 41 and
  210 proposed links to 1 (the correct one) and 0, with the second record's three
  genuine links still validating as `Valid`.
- Root model was read from the end of `own_model_path` (the leaf) while the root pid came
  from the start of `own_pid_path`. Any parent reached via a hit on its child — a
  monograph unit or periodical volume — was therefore reported as `non_linkable_model`
  and silently skipped.

### Added

- New `kramerius-links` review category `identifier_matches_multiple_documents`. When one
  identifier resolves to several Kramerius documents the extra matches are almost always
  wrong metadata on the Kramerius side, so rather than guessing, the validator reports the
  identifier, the match count and a sample of the candidate PIDs for a curator to judge —
  and to pass back to the digitisation team.

- `make check` quality gate (`format-check` + `lint` + `typecheck`) and the supporting
  `format` / `lint-fix` targets.
- Release targets: `set-version`, `tag-version`, `tag-latest`, `release`.
- Local Helm testing against a k3s cluster via k3d (`k3d-*` and `helm-*` targets).
- `deploy/docker-compose/app.env.example` documenting every environment key.

### Fixed

- Both container images were missing `periodic_sync/` and `reports/` from their COPY
  lists, so the API and the worker both died at import with
  `ModuleNotFoundError: No module named 'periodic_sync'`. The packages were added with
  the periodic-sync and report-generation features but never wired into the images.
- `celery-redbeat` was a worker-only extra, but the **API** is what writes the redbeat
  schedule entries — on startup and whenever maintenance / periodic-sync settings are
  saved. It is now a shared dependency. The startup reconciliation is wrapped in
  `except Exception` + a warning, so the missing import silently left default schedules
  (including the orphaned-task reaper) unregistered instead of failing loudly.
- Container builds failed to resolve dependencies. `uv export` pins the git
  dependencies by commit while the SDK's own metadata names the same packages by tag,
  and pip rejected the two forms as conflicting direct URLs. The Containerfiles now
  install uv's already-resolved closure with `--no-deps` instead of letting pip
  re-resolve on top of it, which is also what makes the image reproducible.
- `rebuild_search_vectors` was a silent no-op: it built records with
  `MarcRecord(data=...)`, which is not a valid constructor, so every record raised a
  `ValidationError` that the surrounding `except Exception` swallowed as a warning.
  Now uses `MarcRecord.from_mrc`.
- `ManagedTask` passed its configured blocking timeout as the lock's `blocking` flag,
  so the value was ignored and the sync task blocked for the 30 s default instead of
  the intended 1 s.
- Validator, comparator, and authority-linker loaders fell back to constructing the
  tool with no config when settings stored `null`. Every concrete tool requires one,
  so that path raised `TypeError`; they now fall back to the config model's defaults.
- Validation, comparison, and authority-linking tasks crashed instead of skipping when
  a record was deleted between building the id list and processing it — the `except`
  handler then dereferenced the same `None` while logging.
- `dispatch_task` no longer subscripts `task.data` unguarded for `SyncRecords`.
- `Settings.get` referenced a possibly-unbound local when validation failed.
- `authors` on `CatalogRecord` used a shared mutable `default=[]`.

### Changed

- Ruff lint selection extended with `B` (bugbear) and `SIM` (simplify).
- Client tooling migrated from npm to Bun, and from ESLint + Prettier to Biome.
- Python dependencies migrated from `requirements*.txt` to PEP 621 with `uv`.
- All entities converted from legacy `Column` to `Mapped` / `mapped_column`; nullability
  now comes from the annotation. DDL verified unchanged.
- `Settings.get` / `Settings.upsert` are generic in the schema type, so callers get the
  concrete settings model back instead of the `SettingsSchema` base. `Settings.save` was
  renamed to `Settings.upsert` — it is a classmethod upsert, not the mixin's instance
  `save`, and sharing the name made it an incompatible override.
- `TokenData.user_id` is `str` rather than `str | None`; it is always populated.
- Pydantic `Field(<value>, ...)` defaults changed to `Field(default=<value>, ...)` —
  pyright only recognises the keyword form, so every such model looked all-required.
- `BaseValidator`, `BaseComparator`, and `BaseAuthorityLinker` declare
  `__init__(self, config=None)`, making the config contract explicit.

### Removed

- `deploy/docker-compose/app.env` and `app.oidc.env` are no longer tracked; copy them
  from `app.env.example` instead.

## [1.0.0-rc6]

Release-candidate history predates this changelog and was not backfilled — see the git
log for changes up to and including `1.0.0-rc6`.
