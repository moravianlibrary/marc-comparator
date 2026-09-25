#!/usr/bin/env python3
"""Runs the record pipeline one stage at a time and reports what each cost.

The pipeline is normally one ``ProcessRecords`` task that links, compares and
validates in a single pass, which makes it hard to say which of the three is
expensive. This driver wipes the record tables, syncs a bounded slice of both
catalogues, and then runs the stages separately against the same data — first
cold, then again with every result already present, because "what does it cost
to redo work that is already done" is a different question with a different
answer.

Each stage is bracketed by three instruments:

* the task row itself, for wall clock — its `progress` is a fraction of the
  work-set, not a count, so the size of that set is counted separately here;
* ``pg_stat_statements``, reset before the stage, for the SQL the server ran;
* ``adapters.sql_tracing``, diffed across the stage, for the Python call sites
  that issued it.

Only the third answers "which line asked for this", which is the question this
workload keeps raising. It needs ``worker.sqlTrace=true`` in the chart; without
it the stage still runs and the report simply omits that section.

Everything that changes the cluster goes through the local kubeconfig, never
the caller's $KUBECONFIG — see Kube.kubectl.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
K3D_KUBECONFIG = REPO_ROOT / ".k3d-kubeconfig.yaml"

NAMESPACE = "marc-comparator"
CNPG_CLUSTER = "marc-comparator-db"
DATABASE = "marc"

#: Tables holding records or anything derived from them. Everything here is
#: emptied by --reset; everything absent from it survives, which is the point:
#: `settings`, `users`, `roles` and `plugin_harvest_state` are configuration
#: and bookkeeping, and the harvested datasets themselves live in the plugins'
#: own schemas (plugin_kramerius_links, plugin_marcxml_dump) where no amount of
#: truncating in `public` can reach them.
#:
#: Listed together in one TRUNCATE so the foreign keys between them do not need
#: an ordering — or a CASCADE, which would silently reach tables not named here.
RECORD_TABLES = [
    "catalog_records",
    "authority_links",
    "comparisons",
    "validations",
    "record_reviews",
    "result_snapshots",
    "marc_sectors",
    "marc_record_index",
    # Derived read models, rebuilt by RefreshAnalytics after a run.
    "catalog_records_analytics",
    "facet_cube",
    "facet_cube_histogram",
    # Task history, so the report sees only this benchmark's tasks.
    # report_artifacts is ON DELETE CASCADE from tasks and goes with it.
    "report_artifacts",
    "tasks",
    "celery_taskmeta",
    "celery_tasksetmeta",
]

#: Counted before and after every stage, so a stage that produced nothing is
#: visible as such rather than just fast.
COUNTED_TABLES = [
    "catalog_records",
    "marc_sectors",
    "marc_record_index",
    "authority_links",
    "comparisons",
    "validations",
    "result_snapshots",
]

SQL_TRACE_DIR = "/tmp/sql-trace"


# ─── Cluster access ──────────────────────────────────────────────────────────


class Kube:
    """kubectl against the local k3d cluster, never the caller's context.

    $KUBECONFIG on this machine points at production, so every call here sets
    it explicitly. A missing local kubeconfig is refused rather than falling
    back to whatever the shell is aimed at.
    """

    def __init__(self, kubeconfig: Path = K3D_KUBECONFIG, namespace: str = NAMESPACE):
        if not kubeconfig.exists():
            sys.exit(f"no local cluster kubeconfig at {kubeconfig} — run `make k3d-up` first")
        self.kubeconfig = kubeconfig
        self.namespace = namespace

    def kubectl(self, *args: str, check: bool = True) -> str:
        # The caller's environment with KUBECONFIG overridden, rather than a
        # env built from scratch: kubectl needs HOME for its discovery cache
        # and silently writes a .kube directory into the working tree without
        # it. Only KUBECONFIG has to be wrong-proofed.
        result = subprocess.run(
            ["kubectl", "--namespace", self.namespace, *args],
            env={**os.environ, "KUBECONFIG": str(self.kubeconfig)},
            capture_output=True,
            text=True,
        )
        if check and result.returncode != 0:
            raise RuntimeError(f"kubectl {' '.join(args)} failed:\n{result.stderr.strip()}")
        return result.stdout

    def pod(self, selector: str) -> str:
        name = self.kubectl(
            "get", "pod", "-l", selector, "-o", "jsonpath={.items[0].metadata.name}"
        ).strip()
        if not name:
            raise RuntimeError(f"no pod matching {selector}")
        return name

    @property
    def db_pod(self) -> str:
        return self.pod(f"cnpg.io/cluster={CNPG_CLUSTER},cnpg.io/instanceRole=primary")

    @property
    def worker_pod(self) -> str:
        return self.pod("app.kubernetes.io/component=worker")

    def psql(self, sql: str, *, quiet: bool = True) -> str:
        flags = ["-tAc", sql] if quiet else ["-P", "pager=off", "-c", sql]
        return self.kubectl(
            "exec",
            "-c",
            "postgres",
            self.db_pod,
            "--",
            "psql",
            "-U",
            "postgres",
            "-d",
            DATABASE,
            *flags,
        )

    def worker_sh(self, script: str) -> str:
        return self.kubectl("exec", self.worker_pod, "--", "sh", "-c", script, check=False)

    def admin_credentials(self) -> tuple[str, str]:
        """The deployed admin account, read from the release's own config.

        Not defaulted in the source: the chart's password is per-install, and a
        hard-coded guess here fails as a 401 that looks like a broken script.
        """

        email = self.kubectl(
            "get", "configmap", "marc-comparator-config", "-o", "jsonpath={.data.ADMIN_EMAIL}"
        ).strip()
        encoded = self.kubectl(
            "get", "secret", "marc-comparator-secret", "-o", "jsonpath={.data.ADMIN_PASSWORD}"
        ).strip()
        return email, base64.b64decode(encoded).decode()


# ─── API ─────────────────────────────────────────────────────────────────────


class Api:
    """The application's own HTTP surface — tasks are created the way a user would.

    Deliberately not inserting task rows directly: settings resolution and the
    permission checks are part of what a stage does, and a benchmark that
    skipped them would be measuring a path nothing else takes.
    """

    def __init__(self, base_url: str, email: str, password: str):
        self.client = httpx.Client(base_url=base_url, timeout=60.0)
        self._credentials = {"email": email, "password": password}
        self._login()

    def _login(self) -> None:
        """Log in and carry the session token as a header.

        The token comes back only as a cookie, and that cookie is marked
        Secure — so a client obeying the rules will not send it back over the
        plain-HTTP port-forward, and every call 401s. Reading the value out
        and setting it explicitly is the honest way round that for a local
        driver; the alternative is redeploying the release with
        COOKIE_SECURE=false just to measure it.
        """

        try:
            response = self.client.post("/auth/login", json=self._credentials)
        except httpx.ConnectError:
            sys.exit(
                f"cannot reach the app at {self.client.base_url} — start the forward with\n"
                "  make k3d-port-forward-up"
            )
        if response.status_code != 200:
            sys.exit(f"login failed ({response.status_code}): {response.text[:200]}")

        token = response.cookies.get("access_token")
        if not token:
            sys.exit("login succeeded but returned no access_token cookie")
        self.client.headers["Cookie"] = f"access_token={token}"

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """One retry behind a fresh login.

        Access tokens last fifteen minutes and a stage can run for hours, so
        the token in hand is routinely dead by the time the next stage starts.
        """

        response = self.client.request(method, path, **kwargs)
        if response.status_code == 401:
            self._login()
            response = self.client.request(method, path, **kwargs)
        return response

    def create_task(self, path: str, payload: dict) -> str:
        response = self._request("POST", path, json=payload)
        if response.status_code >= 400:
            raise RuntimeError(f"POST {path} -> {response.status_code}: {response.text[:400]}")
        return response.json()["task_id"]

    def revoke_task(self, task_id: str) -> None:
        response = self._request("PATCH", f"/tasks/{task_id}/revoke")
        if response.status_code >= 400:
            raise RuntimeError(
                f"revoking {task_id} -> {response.status_code}: {response.text[:200]}"
            )


# ─── Instruments ─────────────────────────────────────────────────────────────


def reset_statement_counters(kube: Kube) -> None:
    """Zero pg_stat_statements, creating it if the database restarted.

    CNPG drops the extension during its startup reconciliation, and the
    counters live in shared memory and are lost on restart regardless, so this
    creates rather than assuming an earlier init still holds.
    """

    kube.psql("CREATE EXTENSION IF NOT EXISTS pg_stat_statements;")
    kube.psql("SELECT pg_stat_statements_reset();")


STATEMENT_REPORT = """
SELECT json_agg(row_to_json(t)) FROM (
    SELECT round((total_exec_time / 1000)::numeric, 2) AS total_s,
           round((100 * total_exec_time
                  / nullif(sum(total_exec_time) OVER (), 0))::numeric, 1) AS pct,
           calls,
           round(mean_exec_time::numeric, 3) AS mean_ms,
           left(regexp_replace(query, '\\s+', ' ', 'g'), 110) AS query
    FROM pg_stat_statements
    WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
    ORDER BY total_exec_time DESC
    LIMIT {limit}
) t;
"""


def statement_report(kube: Kube, limit: int) -> list[dict]:
    raw = kube.psql(STATEMENT_REPORT.format(limit=limit)).strip()
    return json.loads(raw) if raw else []


def sql_trace_snapshot(kube: Kube) -> dict[str, dict]:
    """Every pool child's cumulative counters, keyed by "sql @ stack".

    One file per process, so this sums them: which child served a task is an
    accident of the pool and never the answer to anything.
    """

    # Written as one JSON object per file; the loop adds the newlines that make
    # the concatenation parseable, and skips the glob when nothing matched.
    script = f'for f in {SQL_TRACE_DIR}/*.json; do [ -e "$f" ] || continue; cat "$f"; echo; done'
    merged: dict[str, dict] = {}
    for line in kube.worker_sh(script).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            # A file caught mid-write; the next dump is five seconds away.
            continue
        for site in payload.get("sites", []):
            key = site["sql"] + "\n@ " + " < ".join(site["stack"])
            entry = merged.setdefault(
                key, {"sql": site["sql"], "stack": site["stack"], "count": 0, "total_ms": 0.0}
            )
            entry["count"] += site["count"]
            entry["total_ms"] += site["total_ms"]
    return merged


def sql_trace_delta(before: dict[str, dict], after: dict[str, dict]) -> list[dict]:
    """What the stage itself added, by call site.

    A key present only in `after` belongs to a pool child that was not there
    (or had not dumped) when the stage began, so its whole total is charged to
    the stage. That over-states a child forked mid-stage and is the honest
    default: the alternative silently drops its work.
    """

    deltas: list[dict] = []
    for key, entry in after.items():
        base = before.get(key)
        count = entry["count"] - (base["count"] if base else 0)
        total_ms = entry["total_ms"] - (base["total_ms"] if base else 0.0)
        if count <= 0:
            continue
        deltas.append(
            {
                "sql": entry["sql"],
                "stack": entry["stack"],
                "count": count,
                "total_ms": round(total_ms, 1),
            }
        )
    deltas.sort(key=lambda entry: entry["count"], reverse=True)
    return deltas


def table_counts(kube: Kube) -> dict[str, int]:
    selects = ", ".join(f"(SELECT count(*) FROM {table})" for table in COUNTED_TABLES)
    row = kube.psql(f"SELECT {selects};").strip()
    return dict(zip(COUNTED_TABLES, (int(value) for value in row.split("|")), strict=True))


def py_spy_sample(kube: Kube, seconds: int, out_dir: Path, label: str) -> Path | None:
    """A folded-stack sample of the worker, taken mid-stage.

    Folded rather than a flamegraph on purpose: the SVG merges boxes by name,
    which makes it fine for shape and misleading for attributing cost.
    """

    binary = REPO_ROOT / ".profile" / "bin" / "py-spy"
    if not binary.exists():
        print(f"    py-spy not built at {binary} — run `make profile-worker` once; skipping")
        return None

    pod = kube.worker_pod
    kube.kubectl("cp", str(binary), f"{NAMESPACE}/{pod}:/tmp/py-spy", check=False)
    remote = f"/tmp/{label}.txt"
    kube.kubectl(
        "exec",
        pod,
        "--",
        "/tmp/py-spy",
        "record",
        "--pid",
        "1",
        "--subprocesses",
        "--duration",
        str(seconds),
        "--rate",
        "100",
        "--format",
        "raw",
        "--output",
        remote,
        check=False,
    )
    local = out_dir / f"{label}.folded"
    kube.kubectl("cp", f"{NAMESPACE}/{pod}:{remote}", str(local), check=False)
    return local if local.exists() else None


# ─── Stages ──────────────────────────────────────────────────────────────────


@dataclass
class TaskSpec:
    """One task to create and wait for."""

    label: str
    path: str
    payload: dict


#: Counts the record selection a stage walks. Every stage below is given an
#: unfiltered RecordFilter, and each one turns that into the same
#: build_filtered_query over catalog_records — so this is their work-set.
SELECTED_RECORDS = "SELECT count(*) FROM catalog_records"

#: A sync's work-set is the catalogue's answer, not a query, so it is counted
#: afterwards by what it actually touched.
SYNCED_RECORDS = "SELECT count(*) FROM catalog_records WHERE latest_sync >= '{start}'"


@dataclass
class Stage:
    name: str
    description: str
    tasks: list[TaskSpec]
    #: How many records the stage worked on. The task row cannot answer this:
    #: its `progress` is a fraction, and the count behind it lives only in the
    #: worker's memory.
    records_sql: str = SELECTED_RECORDS
    #: Whether that has to be evaluated after the stage rather than before it.
    records_after: bool = False


@dataclass
class TaskResult:
    label: str
    task_id: str
    status: str
    #: The task row's `progress`, which is the fraction of its work-set that is
    #: done (0..1) — not a record count. The count is the stage's own, below.
    completed: float | None
    #: From the task row, so it excludes the queue wait this driver would
    #: otherwise charge to the stage.
    server_seconds: float | None


@dataclass
class StageResult:
    name: str
    description: str
    wall_seconds: float
    tasks: list[TaskResult] = field(default_factory=list)
    counts_before: dict[str, int] = field(default_factory=dict)
    counts_after: dict[str, int] = field(default_factory=dict)
    statements: list[dict] = field(default_factory=list)
    #: The worst `--top` of them; `sql_calls`/`sql_driver_seconds` below are
    #: over *all* of them, so that the stage's totals do not silently change
    #: with where the report happens to be cut off.
    call_sites: list[dict] = field(default_factory=list)
    sql_calls: int = 0
    #: Measured around cursor.execute, so it includes the round trip and the
    #: driver — which is the whole point: compare it against the server's own
    #: figure and the difference is what the round trips cost.
    sql_driver_seconds: float = 0.0
    py_spy: str | None = None
    #: Records in the stage's work-set, counted by Stage.records_sql.
    records: int = 0

    @property
    def finished(self) -> bool:
        """Whether every task ran to completion — a partial run has no rate."""

        return all(task.status == "Success" for task in self.tasks)

    @property
    def ms_per_record(self) -> float | None:
        """Per record of the selection, summed over the stage's tasks.

        Two tasks over the same selection (one per target base) cost two passes
        over it, so their seconds add and the denominator does not.
        """

        if not self.records or not self.finished:
            return None
        server = sum(task.server_seconds or 0 for task in self.tasks)
        return round(server * 1000 / self.records, 1)


def build_stages(args: argparse.Namespace) -> list[Stage]:
    from_date = (datetime.now() - timedelta(days=args.since_days)).isoformat()
    every_record: dict = {}
    linkers = args.linkers
    validators = args.validators

    def link_tasks(prefix: str) -> list[TaskSpec]:
        return [
            TaskSpec(
                f"{prefix}{base}",
                "/authority-linking/task",
                {"linkers": linkers, "target_base": base, "filters": every_record},
            )
            for base in args.target_bases
        ]

    def compare_tasks(prefix: str) -> list[TaskSpec]:
        return [
            TaskSpec(
                f"{prefix}{base}",
                "/comparison/task",
                {"target_base": base, "filters": every_record},
            )
            for base in args.target_bases
        ]

    def validate_tasks(prefix: str) -> list[TaskSpec]:
        return [
            TaskSpec(
                prefix.rstrip("-") or "validate",
                "/validation/task",
                {"validators": validators, "filters": every_record},
            )
        ]

    def process_tasks(label: str) -> list[TaskSpec]:
        return [TaskSpec(label, "/catalog-records/process", every_record)]

    return [
        Stage(
            "sync",
            f"catalogue sync of {', '.join(args.bases)} since {from_date[:10]}",
            [
                TaskSpec(
                    f"sync-{base}",
                    "/catalog-records/sync",
                    {"base": base, "from_date": from_date},
                )
                for base in args.bases
            ],
            records_sql=SYNCED_RECORDS,
            records_after=True,
        ),
        Stage(
            "process",
            "full processing pass (links + comparisons + validations)",
            process_tasks("process"),
        ),
        Stage("link", "authority linking alone", link_tasks("link-")),
        Stage("compare", "comparison alone", compare_tasks("compare-")),
        Stage("validate", "validation alone", validate_tasks("validate-")),
        Stage(
            "rerun-process",
            "processing again, with every result already present",
            process_tasks("rerun-process"),
        ),
        Stage(
            "rerun-link",
            "linking again, with every link already present",
            link_tasks("rerun-link-"),
        ),
        Stage(
            "rerun-compare",
            "comparison again, with every comparison already present",
            compare_tasks("rerun-compare-"),
        ),
        Stage(
            "rerun-validate",
            "validation again, with every validation already present",
            validate_tasks("rerun-validate-"),
        ),
    ]


# ─── Running ─────────────────────────────────────────────────────────────────


def wait_for_task(kube: Kube, task_id: str, poll_seconds: float, timeout_seconds: float) -> dict:
    """Poll the task row until it leaves Pending/Started.

    The row rather than the API: it carries started_at/finished_at, which is
    the stage's own clock without this driver's polling latency in it.
    """

    deadline = time.monotonic() + timeout_seconds
    last_completed = -1.0
    while True:
        row = kube.psql(
            "SELECT status, coalesce(progress, -1), "
            "coalesce(extract(epoch FROM finished_at - started_at), -1) "
            f"FROM tasks WHERE task_id = '{task_id}';"
        ).strip()
        if not row:
            raise RuntimeError(f"task {task_id} vanished from the tasks table")
        status, completed_text, elapsed_text = row.split("|")
        completed = float(completed_text)
        if completed != last_completed:
            # A task whose work-set is not countable yet reports no progress at
            # all; -1 is this query's stand-in for that NULL, not a percentage.
            shown = "size not known yet" if completed < 0 else f"{completed * 100:.1f}%"
            print(f"    {status.lower()}: {shown}   ", end="\r", flush=True)
            last_completed = completed
        if status not in ("Pending", "Started"):
            print(" " * 60, end="\r")
            elapsed = float(elapsed_text)
            return {
                "status": status,
                "completed": None if completed < 0 else completed,
                "server_seconds": None if elapsed < 0 else round(elapsed, 1),
            }
        if time.monotonic() > deadline:
            raise TimeoutError(f"task {task_id} still {status} after {timeout_seconds}s")
        time.sleep(poll_seconds)


def run_stage(stage: Stage, kube: Kube, api: Api, args: argparse.Namespace) -> StageResult:
    print(f"\n── {stage.name} — {stage.description}")

    counts_before = table_counts(kube)
    reset_statement_counters(kube)
    trace_before = sql_trace_snapshot(kube)

    # The database's clock, not this machine's: it is what latest_sync is
    # stamped from, and the two are not guaranteed to agree.
    db_start = kube.psql("SELECT now();").strip()
    records = 0 if stage.records_after else int(kube.psql(stage.records_sql).strip())

    started = time.monotonic()
    results: list[TaskResult] = []
    sampled = False
    for spec in stage.tasks:
        task_id = api.create_task(spec.path, spec.payload)
        print(f"  {spec.label}: {task_id}")
        if args.py_spy_seconds and not sampled:
            # One sample per stage, taken once the stage is past its opening
            # queries and into the loop that dominates it.
            time.sleep(args.py_spy_warmup)
            py_spy_sample(kube, args.py_spy_seconds, args.out, f"{stage.name}")
            sampled = True
        outcome = wait_for_task(kube, task_id, args.poll_seconds, args.task_timeout)
        results.append(TaskResult(label=spec.label, task_id=task_id, **outcome))
        done = outcome["completed"]
        print(
            f"    {outcome['status']} in {outcome['server_seconds']}s"
            + (f" ({done * 100:.0f}% of its work-set)" if done is not None else "")
        )

    wall = round(time.monotonic() - started, 1)
    if stage.records_after:
        records = int(kube.psql(stage.records_sql.format(start=db_start)).strip())
    # The tracer dumps on a timer; give the last one a chance to land so the
    # tail of the stage is not missing from the delta.
    time.sleep(args.trace_settle)

    call_sites = sql_trace_delta(trace_before, sql_trace_snapshot(kube))

    return StageResult(
        name=stage.name,
        description=stage.description,
        wall_seconds=wall,
        tasks=results,
        counts_before=counts_before,
        counts_after=table_counts(kube),
        statements=statement_report(kube, args.top),
        call_sites=call_sites[: args.top],
        sql_calls=sum(entry["count"] for entry in call_sites),
        sql_driver_seconds=round(sum(entry["total_ms"] for entry in call_sites) / 1000, 1),
        py_spy=f"{stage.name}.folded" if args.py_spy_seconds else None,
        records=records,
    )


def reset_records(kube: Kube) -> None:
    """Empty every record table, leaving configuration and plugin data alone."""

    print("── reset — emptying record tables")
    kube.psql(f"TRUNCATE TABLE {', '.join(RECORD_TABLES)} RESTART IDENTITY;")
    remaining = table_counts(kube)
    kept = (
        kube.psql(
            "SELECT (SELECT count(*) FROM settings), (SELECT count(*) FROM users), "
            "(SELECT count(*) FROM plugin_harvest_state), "
            "(SELECT count(*) FROM pg_namespace WHERE nspname LIKE 'plugin\\_%');"
        )
        .strip()
        .split("|")
    )
    print(f"  records now: {sum(remaining.values())}")
    print(
        f"  kept: {kept[0]} settings, {kept[1]} users, "
        f"{kept[2]} harvest states, {kept[3]} plugin schemas"
    )


def refuse_if_busy(kube: Kube, api: Api, revoke: bool) -> None:
    """A stage measured next to somebody else's task measures both."""

    rows = [
        line
        for line in kube.psql(
            "SELECT task_id, type FROM tasks WHERE status IN ('Pending', 'Started');"
        ).splitlines()
        if line.strip()
    ]
    if not rows:
        return
    if not revoke:
        sys.exit(
            f"{len(rows)} task(s) are still Pending/Started — their work would land in\n"
            "these measurements. Revoke them in the UI, or re-run with --revoke-running."
        )

    print(f"── revoking {len(rows)} running task(s)")
    for row in rows:
        task_id, task_type = row.split("|")
        # Through the API, not by updating the row: the row is what a *new*
        # delivery checks, while a task already running is stopped by the
        # in-memory broadcast that only this endpoint sends.
        api.revoke_task(task_id)
        print(f"  revoked {task_type} {task_id}")

    deadline = time.monotonic() + 120
    while (
        kube.psql("SELECT count(*) FROM tasks WHERE status IN ('Pending', 'Started');").strip()
        != "0"
    ):
        if time.monotonic() > deadline:
            sys.exit("a revoked task is still running after 2 minutes; stop it before measuring")
        time.sleep(5)


# ─── Reporting ───────────────────────────────────────────────────────────────


def print_stage_report(result: StageResult, top: int) -> None:
    grew = {
        table: result.counts_after[table] - result.counts_before[table]
        for table in COUNTED_TABLES
        if result.counts_after[table] != result.counts_before[table]
    }
    print(
        f"\n  {result.name}: {result.wall_seconds}s wall, {result.records} records"
        + (f", {result.ms_per_record} ms/record" if result.ms_per_record else "")
    )
    if grew:
        print("  rows: " + ", ".join(f"{table} {delta:+d}" for table, delta in grew.items()))

    if result.statements:
        server_s = sum(entry["total_s"] for entry in result.statements)
        share = server_s / result.wall_seconds * 100 if result.wall_seconds else 0
        print(
            f"\n  server-side SQL: {server_s:.1f}s over {result.wall_seconds}s wall "
            f"({share:.1f}% — the rest is the worker, the network and waiting)"
        )
        print(f"  {'total_s':>8} {'pct':>5} {'calls':>8} {'mean_ms':>8}  query")
        for entry in result.statements[:top]:
            print(
                f"  {entry['total_s']:>8} {entry['pct']:>5} {entry['calls']:>8} "
                f"{entry['mean_ms']:>8}  {entry['query'][:90]}"
            )

    if result.sql_calls:
        share = result.sql_driver_seconds / result.wall_seconds * 100 if result.wall_seconds else 0
        print(
            f"\n  SQL from the worker's side: {result.sql_driver_seconds}s over "
            f"{result.wall_seconds}s wall ({share:.1f}%), {result.sql_calls} statements"
        )
        print(
            "  What neither this nor the server figure above accounts for is Python and\n"
            "  whatever the task waits on that is not the database."
        )

    if result.call_sites:
        print(f"\n  Worst {len(result.call_sites)} call sites (innermost frame first):")
        print(f"  {'calls':>8} {'total_ms':>9}  site")
        for entry in result.call_sites[:top]:
            origin = entry["stack"][0] if entry["stack"] else "?"
            print(f"  {entry['count']:>8} {entry['total_ms']:>9}  {origin}")
            print(f"  {'':>18}  {entry['sql'][:88]}")
            for frame in entry["stack"][1:4]:
                print(f"  {'':>18}    ← {frame}")
    else:
        print("\n  (no call-site data — worker.sqlTrace is off in the chart)")


def print_summary(results: list[StageResult]) -> None:
    print("\n" + "═" * 78)
    print("SUMMARY")
    print(
        f"  {'stage':<16} {'wall_s':>8} {'records':>9} {'ms/rec':>8} "
        f"{'sql_calls':>10} {'sql/rec':>8} {'sql_s':>7}"
    )
    for result in results:
        per_record = round(result.sql_calls / result.records, 1) if result.records else "-"
        print(
            f"  {result.name:<16} {result.wall_seconds:>8} {result.records:>9} "
            f"{str(result.ms_per_record or '-'):>8} {result.sql_calls:>10} "
            f"{str(per_record):>8} {result.sql_driver_seconds:>7}"
        )
    print(
        "\n  ms/rec is the task's own clock over its work-set. sql_calls and sql_s cover\n"
        "  every statement the stage issued, not only the call sites listed above."
    )


# ─── Entry point ─────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--stages",
        nargs="*",
        default=None,
        help="stages to run (default: all). reset is separate, see --no-reset",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="keep existing records instead of emptying the record tables",
    )
    parser.add_argument(
        "--revoke-running",
        action="store_true",
        help="revoke tasks that are already running instead of refusing to start",
    )
    parser.add_argument(
        "--since-days", type=int, default=2, help="sync window, in days back from now (default: 2)"
    )
    parser.add_argument("--bases", nargs="+", default=["MZK01", "MZK03"])
    parser.add_argument("--target-bases", nargs="+", default=["SKC"])
    parser.add_argument("--linkers", nargs="+", default=["marcxml-dump", "knihovny-cz"])
    parser.add_argument("--validators", nargs="+", default=["kramerius-links"])
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument(
        "--email", default=None, help="default: ADMIN_EMAIL from the deployed config map"
    )
    parser.add_argument(
        "--password", default=None, help="default: ADMIN_PASSWORD from the deployed secret"
    )
    parser.add_argument("--top", type=int, default=15, help="rows per report section")
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--task-timeout", type=float, default=6 * 3600)
    parser.add_argument(
        "--trace-settle",
        type=float,
        default=7.0,
        help="wait after a stage for the tracer's last dump (dumps every 5s)",
    )
    parser.add_argument(
        "--py-spy-seconds",
        type=int,
        default=0,
        help="take a folded-stack sample of this length during each stage",
    )
    parser.add_argument(
        "--py-spy-warmup",
        type=float,
        default=30.0,
        help="how far into a stage to start that sample",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / ".benchmark" / datetime.now().strftime("%Y%m%d-%H%M%S"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    kube = Kube()
    email, password = kube.admin_credentials()
    api = Api(args.api, args.email or email, args.password or password)
    print(f"→ cluster: {kube.kubeconfig}")
    print(f"→ report:  {args.out}")

    refuse_if_busy(kube, api, args.revoke_running)

    stages = build_stages(args)
    if args.stages:
        known = {stage.name for stage in stages}
        unknown = set(args.stages) - known
        if unknown:
            sys.exit(f"unknown stage(s): {', '.join(sorted(unknown))}\nknown: {', '.join(known)}")
        stages = [stage for stage in stages if stage.name in args.stages]

    if not args.no_reset:
        reset_records(kube)

    results: list[StageResult] = []
    try:
        for stage in stages:
            result = run_stage(stage, kube, api, args)
            results.append(result)
            print_stage_report(result, args.top)
            # Written after every stage, so an interrupted run still leaves
            # everything it had finished measuring.
            (args.out / "report.json").write_text(
                json.dumps([asdict(result) for result in results], indent=2)
            )
    except KeyboardInterrupt:
        print("\ninterrupted — the stages already finished are in report.json")

    if results:
        print_summary(results)
        print(f"\n→ {args.out / 'report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
