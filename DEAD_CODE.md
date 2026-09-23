# Dead code and compatibility shims

Working note, to be acted on **after** the current branch is tested and committed,
then deleted along with the code it describes.

None of this originates from the current branch — the cron, `marcxml-dump` rename,
task-target and linker work left nothing unused behind. All compatibility shims
written during that work (legacy `interval_hours`, the `skc` → `marcxml-dump`
settings and selection mapping) have already been removed, since prod is being
rolled back with the dev cluster.

Line numbers are from the working tree at the time of writing; re-check before
deleting, especially after a rebase.

---

## 1. Safe to delete

Unambiguous. No caller, no framework registration, no external surface.

### `app/adapters/database.py:46-53` — `database_session`

A third session helper, byte-for-byte identical to `db_session_generator` above it
apart from the `@contextmanager` decorator. Zero callers.

The two live ones stay:

| helper | uses | role |
| --- | --- | --- |
| `get_db_session` | 18 | returns a session directly |
| `db_session_generator` | 7 | FastAPI dependency |
| `database_session` | **0** | delete |

`database_session` is the only user of the `from contextlib import contextmanager`
import on line 1, so that goes with it.

### `app/entities/task.py:49` — `# Retry = "Retry"`

Commented-out `TaskStatus` member. The string `"Retry"` appears nowhere else in
the repo, so no stored row or API payload can carry it. Ruff's `ERA001` flags it;
that rule is not enabled in the project config.

---

## 2. Judgement calls

Dead by the same measure, but deleting them asserts something about intent.
Decide, don't default.

### 2a. Eight functions in the vendored comparison engine

Defined, never called, not re-exported from any `__init__.py`, not mentioned in
`sdk/README.md`:

| file | line | symbol |
| --- | --- | --- |
| `comparators/intiim_engine/checks/typo.py` | 15 | `damerau_levenshtein` |
| `comparators/intiim_engine/io_marc.py` | 43 | `load_records` |
| `comparators/intiim_engine/io_marc.py` | 63 | `load_records_from_bytes` |
| `comparators/intiim_engine/llm.py` | 252 | `ollama_generate` |
| `comparators/intiim_engine/llm.py` | 256 | `load_llm` |
| `comparators/intiim_engine/llm_verify.py` | 67 | `apply_llm_verification` |
| `comparators/intiim_engine/normalizers.py` | 35 | `strip_diacritics` |
| `comparators/intiim_engine/normalizers.py` | 39 | `alnum_lower` |

(paths relative to `sdk/marc_comparator/`)

`intiim_engine` is a vendored engine rather than code written for this repo. If it
is still synced from an upstream source, deleting parts of it makes the next sync
a merge instead of a copy — that cost may outweigh the tidiness. If it is now
simply ours, delete them.

Note `io_marc.py` is also where the pymarc compatibility branch lives (§4); the
two decisions interact, since both `load_records*` functions are the only callers
of `_as_dict`, which is what contains that branch.

### 2b. The facets-preview feature — live endpoint, no caller

- `app/catalog_records/controller.py:56-61` — `POST /catalog-records/facets-preview`,
  permission-gated on `ReadRecords`, fully implemented
- `client/src/features/records/plots/use-facets.ts:22` — `useFacetPreview`, the
  hook that calls it, referenced by no component

So the endpoint is reachable and serving a UI that does not exist. Either wire the
hook into the plots view or delete both ends — but delete *both*: leaving the
endpoint without a client keeps an untested, permission-gated query path in the
API surface.

### 2c. Unused client type exports

| file | line | symbol |
| --- | --- | --- |
| `src/types/role.ts` | 16 | `EditRoleRequest` |
| `src/features/settings/schemas.ts` | 29 | `CatalogSettingsFormValues` |
| `src/features/settings/schemas.ts` | 37 | `TaskSettingsFormValues` |
| `src/features/settings/schemas.ts` | 107 | `ProcessRecordsSettingsFormValues` |
| `src/features/settings/schemas.ts` | 128 | `MaintenanceSettingsFormValues` |
| `src/features/settings/schemas.ts` | 146 | `PeriodicSyncSettingsFormValues` |

The other four `*FormValues` aliases (AuthorityLinking, Validation, Comparison,
PluginHarvest) **are** used, so these five are an asymmetry rather than a pattern.
They cost nothing at runtime — the argument for keeping them is that the next form
to need one finds it already there. Weak either way; pick one and make all nine
consistent.

---

## 3. Do NOT delete — verified live despite looking unused

A naive "exported but never referenced" scan flags **121** Python symbols. Almost
all are called by name or decorator rather than by reference. Recorded here so a
future cleanup does not rediscover and remove them.

- **Every FastAPI route handler** (`app/*/controller.py`) — invoked via `@router.*`
- **Every pytest class and fixture** — collected by name
- **Every CLI command** (`sdk/marc_comparator/cli/__main__.py`) — decorator-registered
- `app/adapters/tasks.py:101` — `_reset_db_pool`, decorated
  `@worker_process_init.connect`. Drops DB connections inherited from the prefork
  parent; without it forked workers share the parent's sockets and corrupt the
  protocol (SSL EOF / bad record mac). **Deleting this breaks workers under load,
  intermittently.**
- `app/entities/user.py:59` — `UserRole`, imported by `app/migrations/env.py` with
  `# noqa: F401` so Alembic autogenerate sees the table
- `app/entities/catalog_record.py` — `set_id_before_insert`, a SQLAlchemy event
  listener; its `mapper`/`connection` parameters are required by the signature and
  correctly marked `# noqa: F841`

---

## 4. The one remaining compatibility branch

`sdk/marc_comparator/comparators/intiim_engine/io_marc.py:23` — *"Legacy pymarc
fallback: subfields is a flat [code, value, …] list."*

`_as_dict` branches on whether `f.subfields[0]` exposes `.code`/`.value`. pymarc 5
does; pymarc 4 returned a flat list. Installed version is **5.4.0**, so the
fallback is currently unreachable — but `sdk/pyproject.toml:22` declares
`"pymarc"` with **no version constraint**, so a resolver is free to pick 4.x and
the branch becomes live again.

This is a dependency decision, not a cleanup:

- **Pin `pymarc>=5` and delete the branch** — preferred. The SDK already requires
  pymarc 5 semantics everywhere else; the unpinned declaration is the actual bug.
- **Keep the branch** — only if the SDK must stay installable alongside pymarc 4
  for an external consumer.

Do not delete the branch without pinning: that trades a dead branch for a silent
wrong-output path (subfields quietly mis-parsed) on an old pymarc.

---

## Re-verifying before deletion

Unused Python definitions (expect many false positives — cross-check against §3):

```sh
grep -rn "\bSYMBOL\b" --include=*.py app sdk | grep -v '\.venv'
```

One occurrence means the definition only.

Unused client exports:

```sh
cd client && grep -rn "\bSYMBOL\b" src
```

Commented-out code:

```sh
cd app && .venv/bin/python -m ruff check --select ERA001 . ../sdk
```

After any deletion, both must stay clean:

```sh
make check
cd app && .venv/bin/python -m pytest tests/unit tests/db -q
```

`make test` runs everything including integration, which needs Redis reachable on
`localhost:6379` — without it, six task-enqueue tests fail on connection refused
(`tests/integration/{test_authority_linking,test_catalog_controller,test_comparison,test_validation}.py`).
That is an environment failure, not a regression.
