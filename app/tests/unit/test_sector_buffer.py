from unittest.mock import MagicMock

from adapters.marc_sectors import SectorBuffer


class TestSectorBufferSessionGetter:
    def test_uses_session_getter(self):
        """SectorBuffer should call the getter each time it needs the session."""
        session_a = MagicMock()
        session_b = MagicMock()
        sessions = iter([session_a, session_b])
        getter = lambda: next(sessions)

        buffer = SectorBuffer(getter)

        assert buffer.db is session_a
        assert buffer.db is session_b
