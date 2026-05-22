# MARC storage benchmark — results

Benchmark of **118,691 MARC21 binary records** (~238 MB raw) in PostgreSQL 16: storage layout comparison and read/rewrite latency. Aleph system numbers are **dense** (Z39.50 `scan @attr 1=12`: consecutive nine-digit sysnos, gap = 1, ~one record per integer sysno).

---

## 1. Methodology

### 1.1 Storage benchmark

**Corpus:** one file per record; stable `gid` from sorted path order (0…118690).  
**Raw size:** 238,068,373 bytes (~227 MiB).  
**Postgres:** 16, client-driven load and timing (round-trip + app decode/compress included).

**Approaches:**

| Code | Layout |
|------|--------|
| A | One row per record, `BYTEA` `STORAGE EXTERNAL` (TOAST uncompressed) |
| B | One row per record, `STORAGE EXTENDED` (TOAST lz4) |
| C | Application zstd batches: N records concatenated in `gid` order, one `BYTEA` per block, `STORAGE EXTERNAL` |

**Parameters swept (C):** batch size 100, 256, 512, 1000, 1024, 2048, 10000 × zstd levels 3, 5, 7, 9, 11.

**Storage metrics** (post-load, before updates):

| Metric | Definition |
|--------|------------|
| Payload size | Sum of `pg_column_size(payload)` — primary comparison metric |
| On-disk relation size | `pg_total_relation_size` — heap + indexes + TOAST |

**Latency metrics:** sample `gid=59345`; 10 warmup + 40 iterations; mean ms.

| Operation | Definition |
|-----------|------------|
| Read | Fetch row/block → decompress if batched → parse MARC leader → return one record |
| Rewrite | `SELECT … FOR UPDATE` → decode payload → change one byte in target record → write back → `COMMIT` (full block recompress for batched layout) |

**Caveats:** TOAST dead tuples inflate on-disk size after in-place blob updates; batch 10000 is archive-scale only; absolute ms are host-dependent — relative curves drove conclusions. Full matrix load: ~137 s.

---

## 2. Results — PostgreSQL storage (post-load)

**Raw corpus:** 238 MB.

### Baselines

| Approach | Payload | On-disk (approx.) | vs raw |
|----------|--------:|------------------:|-------:|
| Per-record, TOAST uncompressed | 238 MB | 271 MB | ~100% |
| Per-record, TOAST lz4 | 191 MB | 215 MB | ~80% |

### Batched zstd — payload (MB)

| batch → | 100 | 256 | 512 | 1000 | 1024 | 2048 | 10000 |
|---------|----:|----:|----:|-----:|-----:|-----:|------:|
| zstd -3 | 58.3 | 54.9 | 53.2 | 52.1 | 52.0 | 51.3 | 50.7 |
| zstd -5 | 55.3 | 52.0 | 50.0 | 48.5 | 48.5 | 47.5 | 46.7 |
| zstd -7 | 53.3 | 49.4 | 47.2 | 45.4 | 45.3 | 44.1 | 43.1 |
| zstd -9 | 51.5 | 47.8 | 45.5 | 43.5 | 43.5 | 41.8 | 40.1 |
| zstd -11 | 50.9 | 47.1 | 44.6 | 42.4 | 42.3 | 40.5 | 38.4 |

Most payload gain from batching appears by **256**; higher zstd levels give diminishing returns (~2 MB from -7 to -11 at batch 256).

---

## 3. Results — read and rewrite latency

### Baselines

| Approach | Read (ms) | Rewrite (ms) |
|----------|----------:|-------------:|
| TOAST uncompressed | 0.12 | 2.43 |
| TOAST lz4 | 0.16 | 2.80 |

### zstd -7 by batch size

| Batch | Read (ms) | Rewrite (ms) |
|------:|----------:|-------------:|
| 100 | 0.18 | 2.59 |
| 256 | 0.47 | 5.71 |
| 512 | 0.82 | 10.52 |
| 1000 | 2.03 | 22.06 |
| 1024 | 2.06 | 17.99 |
| 2048 | 3.45 | 34.62 |
| 10000 | 18.22 | 200.01 |

### zstd level at batch 256

| Level | Payload (MB) | Read (ms) | Rewrite (ms) |
|------:|-------------:|----------:|-------------:|
| -7 | 49.4 | 0.47 | 5.71 |
| -9 | 47.8 | 0.41 | 6.49 |
| -11 | 47.1 | 0.65 | 8.17 |

### Extreme: zstd -11, batch 10000

Read **18.5 ms**, rewrite **424 ms**.

---

## 4. Brief recommendation

| Layout | Payload | Read | Rewrite | Notes |
|--------|--------:|-----:|--------:|-------|
| Per-record TOAST lz4 | 191 MB | 0.16 ms | 2.8 ms | Postgres-native baseline |
| **zstd -7, 256/block** | **49 MB** | **0.47 ms** | **5.7 ms** | **Default** — ~4× smaller than TOAST lz4, sub-ms reads |
| zstd -9, 256/block | 48 MB | 0.41 ms | 6.5 ms | ~1.6 MB smaller; low write rate |
| zstd -7, 10000/block | 43 MB | 18 ms | 200 ms | Bulk/archive only |

**Storage blocks:** with dense sysnos, blocks can be aligned to sysno order (e.g. ~256 consecutive sysnos per block); benchmark batches used stable `gid` (load order) instead.

**Operations:** prefer append-only or copy-on-write blocks over in-place rewrites on large blobs; plan vacuum on tables with frequent `BYTEA` updates.
