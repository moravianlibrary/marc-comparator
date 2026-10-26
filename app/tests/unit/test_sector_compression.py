"""Sector compression used from several threads at once.

FastAPI runs sync endpoints in a thread pool, so two requests for MARC can
decompress sectors at the same moment. A shared zstd instance corrupts both:
the record detail failed with "Data corruption detected" and worked on retry.
"""

import os
from concurrent.futures import ThreadPoolExecutor

from adapters.marc_sectors import _compressor, _decompressor

PAYLOADS = [os.urandom(2_000) + bytes(200_000) + os.urandom(2_000) for _ in range(8)]


def _round_trips(index: int) -> int:
    payload = PAYLOADS[index]
    failures = 0
    for _ in range(100):
        if _decompressor.decompress(_compressor.compress(payload)) != payload:
            failures += 1
    return failures


def test_concurrent_threads_round_trip_their_own_sectors():
    with ThreadPoolExecutor(max_workers=len(PAYLOADS)) as pool:
        failures = sum(pool.map(_round_trips, range(len(PAYLOADS))))

    assert failures == 0  # each thread reads back exactly what it wrote
