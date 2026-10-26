"""Run a source a little ahead of the loop that consumes it."""

import logging
import threading
from collections.abc import Generator, Iterable, Iterator
from itertools import islice
from queue import Queue

logger = logging.getLogger(__name__)

#: Sentinel put on the queue when the source is exhausted or has failed.
_DONE = object()


def read_ahead[T](source: Iterator[T], ahead: int) -> Generator[T]:
    """Yield from ``source`` while it keeps working on what comes next.

    A paged remote source alternates between waiting on a request and being
    walked, and neither overlaps the other: the OAI catalogue sync spent about
    470 ms fetching each page of thirty records and roughly twice that writing
    them, one after the other. Reading ahead puts the fetching on its own
    thread, so a page is on its way while the previous one is being stored.

    ``ahead`` bounds how far in front the source may get, and with it how much
    is held in memory. The source must not touch anything the consumer touches
    — a database session above all — since the two now run at the same time.

    An exception from the source is re-raised here, in the consumer's own
    stack, once the items it did produce have been yielded.
    """

    queue: Queue = Queue(maxsize=ahead)
    stop = threading.Event()
    failure: list[BaseException] = []

    def produce() -> None:
        try:
            for item in source:
                # A consumer that stopped early is not owed the rest, and the
                # thread must not block forever on a queue nobody reads.
                while not stop.is_set():
                    try:
                        queue.put(item, timeout=0.2)
                        break
                    except Exception:
                        continue
                if stop.is_set():
                    return
        except BaseException as error:  # noqa: BLE001 - re-raised in the consumer
            failure.append(error)
        finally:
            queue.put(_DONE)

    thread = threading.Thread(target=produce, name="read-ahead", daemon=True)
    thread.start()
    try:
        while True:
            item = queue.get()
            if item is _DONE:
                break
            yield item
    finally:
        stop.set()
        # Drain whatever the producer was blocked on so it can notice and end.
        while not queue.empty():
            queue.get_nowait()
        thread.join(timeout=5)

    if failure:
        raise failure[0]


def chunks[T](source: Iterable[T], size: int) -> Iterator[list[T]]:
    """Group a stream into lists of ``size``, without draining it first.

    The last group is whatever is left. Lazy on purpose: the sources this is
    used on run to hundreds of thousands of records, and collecting one to
    slice it would undo the point of streaming it at all.
    """

    iterator = iter(source)
    while chunk := list(islice(iterator, size)):
        yield chunk
