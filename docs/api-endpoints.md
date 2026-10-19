# API guide

The running FastAPI application serves the current, complete request and
response schema at `/docs` and `/openapi.json`. Consult that schema for exact
fields, validation rules, status codes and permissions. Routes are registered
in `app/app.py`; their handlers live in each feature's `controller.py`.

| Area | Route prefix | Main operations |
| --- | --- | --- |
| Authentication | `/auth` | Sign up, log in/out, refresh and account details; optional OIDC |
| Catalog records | `/catalog-records` | Search, facets, MARC, saved comparisons/validations, reviews, fetch, sync and process |
| Authority linking | `/authority-linking` | Start linking; inspect candidate MARC; list, create and withdraw cataloguer claims |
| Comparison | `/comparison` | Run comparison tasks |
| Validation | `/validation` | Run validation tasks |
| Reports | `/reports` | List and download generated task artifacts |
| Tasks | `/tasks` | Search own/all tasks, read logs, revoke and delete |
| Settings | `/settings` | System and record-tool settings |
| Access control | `/access-control` | Users, roles and permissions |
| Maintenance | `/maintenance` | Analytics refresh, sector compaction, task cleanup and related jobs |
| System | `/system` | Health, version information and locks |
| Events | `/ws` | Authenticated task and lock notifications |

The search request accepts a `RecordFilter` from
`app/catalog_records/models.py`. It includes source/record fields, processed
and broken state, comparison score bounds on the **0–15 scale**, validation
results, link outcomes, alternatives, claims and claim review flags. Analytics
and facets are served by maintained PostgreSQL tables, including
`catalog_records_analytics` and facet cubes.

Linking stores an answer row and selected alternatives per record and target
base. Cataloguer verdicts use the candidate's natural key and persist across
linking runs. See [linking and review](linking-review.md) for the behavior and
permissions. Kramerius validation can produce repair, normalization, deletion
and review artifacts; see the [dated report audit](kramerius-report-audit.md)
for checks before an Aleph import.
