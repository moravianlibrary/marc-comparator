# Dead code and compatibility shims

Working note. Two decisions are left; once they are made this file goes with the
code it describes.

## Removed

- `app/adapters/database.py` — `database_session`, a third session helper
  identical to `db_session_generator` apart from the decorator, with no callers.
  The `contextlib.contextmanager` import went with it.
- `app/entities/task.py` — the commented-out `# Retry = "Retry"` status.
- `client/src/features/settings/schemas.ts` — five unused `*FormValues` aliases
  (Catalog, Task, ProcessRecords, Maintenance, PeriodicSync). The four that are
  used remain.
- `client/src/types/role.ts` — `EditRoleRequest`.
- The pymarc compatibility branch in `io_marc.py`, with `pymarc>=5` pinned in
  `sdk/pyproject.toml` first so the pin states what the code already required.
- All the settings compatibility shims written during the cron and linker
  renames (legacy `interval_hours`, `skc` → `marcxml-dump`), since prod is
  rebuilt from empty.

## Still to decide

### The vendored comparison engine

Eight functions in `sdk/marc_comparator/comparators/intiim_engine/` are defined,
never called, not re-exported and not documented:

| file | symbol |
| --- | --- |
| `checks/typo.py` | `damerau_levenshtein` |
| `io_marc.py` | `load_records`, `load_records_from_bytes` |
| `llm.py` | `ollama_generate`, `load_llm` |
| `llm_verify.py` | `apply_llm_verification` |
| `normalizers.py` | `strip_diacritics`, `alnum_lower` |

`intiim_engine` is vendored rather than written here. If it is still synced from
upstream, deleting parts of it turns the next sync into a merge; if it is now
simply ours, delete them. Note `load_records` and `load_records_from_bytes` are
the only callers of `_as_dict`, so removing them makes that dead too.

### The facets-preview feature

- `app/catalog_records/controller.py` — `POST /catalog-records/facets-preview`,
  permission-gated and fully implemented
- `client/src/features/records/plots/use-facets.ts` — `useFacetPreview`, the hook
  that calls it, referenced by no component

Wire the hook into the plots view, or delete both ends. Delete *both*: leaving
the endpoint without a caller keeps an untested, permission-gated query path in
the API surface.

## Do NOT delete — verified live despite looking unused

A naive "exported but never referenced" scan flags 121 Python symbols. Almost
all are called by name or decorator.

- Every FastAPI route handler, pytest class and CLI command
- `app/adapters/tasks.py` — `_reset_db_pool`, decorated
  `@worker_process_init.connect`. Drops DB connections inherited from the prefork
  parent; without it forked workers share the parent's sockets and corrupt the
  protocol. **Deleting this breaks workers intermittently under load.**
- `app/entities/user.py` — `UserRole`, imported by `app/migrations/env.py` with
  `# noqa: F401` so Alembic autogenerate sees the table
- `app/entities/catalog_record.py` — `set_id_before_insert`, a SQLAlchemy event
  listener whose unused parameters are required by the signature

## Investigated and deliberately left alone

`_normalize_isbn` keeps only the first whitespace token, so a space-separated
ISBN would key as `978`. Measured against 5700 real 020$a subfields sampled
across the whole dump: the current normaliser and a length-validating
alternative agree on **100%** of them. Changing it would alter stored keys and
force a re-harvest for no measured benefit.

## Re-verifying

```sh
grep -rn "\bSYMBOL\b" --include=*.py app sdk | grep -v '\.venv'   # 1 hit = definition only
cd client && grep -rn "\bSYMBOL\b" src
cd app && .venv/bin/python -m ruff check --select ERA001 . ../sdk  # commented-out code
```

After any deletion:

```sh
make check
cd app && .venv/bin/python -m pytest tests/unit tests/db -q
```

`make test` also runs integration, which needs Redis on `localhost:6379`; without
it six task-enqueue tests fail on connection refused, which is the environment,
not a regression.
