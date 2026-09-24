"""Reading a source ahead of the loop that consumes it."""

import threading
import time

import pytest

from adapters.pipelining import read_ahead


def test_yields_everything_in_order():
    assert list(read_ahead(iter(range(50)), ahead=4)) == list(range(50))


def test_the_source_runs_while_the_consumer_works():
    # The point of the whole thing: a page is fetched while the previous one
    # is being stored, rather than after.
    produced: list[float] = []

    def source():
        for n in range(6):
            time.sleep(0.02)
            produced.append(time.perf_counter())
            yield n

    start = time.perf_counter()
    for _ in read_ahead(source(), ahead=6):
        time.sleep(0.02)
    elapsed = time.perf_counter() - start

    # Serially this is 6 * (20 + 20) ms; overlapped it is a little over half.
    assert elapsed < 0.20
    assert len(produced) == 6


def test_a_failing_source_raises_in_the_consumer():
    def source():
        yield 1
        yield 2
        raise RuntimeError("the catalogue went away")

    seen = []
    with pytest.raises(RuntimeError, match="the catalogue went away"):
        for item in read_ahead(source(), ahead=4):
            seen.append(item)

    # What it did produce is delivered before the failure surfaces.
    assert seen == [1, 2]


def test_a_consumer_that_stops_early_does_not_leave_the_thread_running():
    # A queue nobody reads would otherwise block the producer for good.
    started = threading.active_count()

    def source():
        yield from range(10_000)

    for item in read_ahead(source(), ahead=2):
        if item == 3:
            break

    deadline = time.perf_counter() + 5
    while threading.active_count() > started and time.perf_counter() < deadline:
        time.sleep(0.05)
    assert threading.active_count() == started


def test_an_empty_source_is_fine():
    assert list(read_ahead(iter(()), ahead=4)) == []
