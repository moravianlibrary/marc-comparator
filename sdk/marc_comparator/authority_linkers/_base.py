from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from marcdantic import MarcRecord
from marcdantic.context import MarcContext
from pydantic import BaseModel

from ..comparators import BaseComparator, RecordComparisonResult
from ..harvest import HarvestCapable


class MatchRoute(StrEnum):
    """What found the candidate, which is not the same as how good it is.

    Retrieval and scoring answer different questions: retrieval answers "is
    this the same work", scoring answers "how far apart are these two records".
    A pair both catalogues give the same ISBN scores low when they describe the
    same book very differently — which is a finding, not a bad link — while two
    unrelated books sharing a generic title score low because they are
    unrelated. Only the route tells those apart, so a linker that retrieves
    several ways reports which one it used and lets the caller set a floor per
    route.
    """

    #: Both records carry the same ISBN, ISSN, ČNB, OCLC number or UUID.
    Identifier = "identifier"
    #: Nothing identified the record; the titles normalize alike.
    Title = "title"
    #: The target catalogue already considers the two records the same work.
    Dedup = "dedup"


#: How to parse a record belonging to somebody else's catalogue.
#:
#: Records we sync are ours to fix, so they are held to marcdantic's default
#: of 001, 005 and 008 — one that will not parse is broken, and says so. A
#: match candidate fetched from the union catalogue is neither ours to fix nor
#: ours to record: there is no row to call broken, so refusing it only removes
#: it from the pool and lowers recall on *our* records, silently.
#:
#: 005 is the date and time of the record's latest transaction and 008 is its
#: fixed-length data elements. Neither says anything about whether two records
#: describe the same book, which is the only question asked of a candidate.
CANDIDATE_MARC_CONTEXT = MarcContext(mandatory_fields=["001"])


@dataclass(slots=True)
class AuthorityLink:
    """
    Represents a link between a bibliographic MARC record
    and an authority record.

    Attributes
    ----------
    base:
        The authority base (e.g., "MZK01", "KNAV", "SKC").
    system_number:
        The unique identifier in the authority system.
    record:
        The MARC authority record that was linked.
    confidence:
        An optional numeric score (0-1) indicating confidence in the link.
    """

    base: str
    system_number: str
    record: MarcRecord
    confidence: float | None = None

    #: The comparison the linker measured between the two records, when it
    #: measured one. A linker that scores its candidates has already compared
    #: the pair it chose, and that is the same pair the pipeline goes on to
    #: compare; carrying the result lets the host decide whether to recompute
    #: it. Only usable when the linker was given the host's own comparator.
    comparison: RecordComparisonResult | None = None

    #: How the candidate was retrieved. Read alongside ``confidence`` it says
    #: what a low score means: weak agreement between records known to be the
    #: same work, or a candidate that was never more than a guess.
    matched_by: MatchRoute | None = None


@dataclass(slots=True)
class LinkRequest:
    """One upcoming ``run`` call, announced ahead of time.

    The fields are exactly ``run``'s arguments, so a linker can answer a
    prefetched request without being told twice what it is being asked.
    """

    base: str
    system_number: str
    record: MarcRecord
    target_base: str


class BaseAuthorityLinker(HarvestCapable, ABC):
    """
    Abstract base class for MARC authority linkers.

    Subclasses implement logic to link catalog records to authority records
    based on metadata, identifiers, or heuristics.
    """

    config_model: type[BaseModel] | None = None

    def __init__(self, config: BaseModel | None = None) -> None:
        #: Linkers declaring a ``config_model`` are constructed with an
        #: instance of it; the rest take no config at all.
        self.config = config

    def bind_comparator(self, comparator: BaseComparator) -> None:
        """Use the host's comparator to judge candidates, instead of a default.

        A linker that ranks candidates needs a comparator, and building its own
        means scoring on whatever scale that default happens to have. The host
        configures one scale for the whole system; a gate measuring against a
        different one makes a linker's ``minimum_confidence`` mean something
        other than the score an operator is shown.

        The host owns the decision of what to bind — in particular whether the
        bound comparator may call an LLM, which a per-candidate gate cannot
        afford however the comparison feature itself is configured.
        """

        self._comparator = comparator

    async def prefetch(self, requests: Sequence[LinkRequest]) -> None:
        """Warm whatever ``run`` would otherwise fetch one record at a time.

        The host announces a window of upcoming calls so a linker that talks to
        a remote service can collapse them into one request and answer the
        window from memory. Doing nothing is always correct: ``run`` must still
        work for a record that was never announced, and a linker answering from
        local storage has nothing to gain here.

        The window may be a superset of what ``run`` is finally asked about,
        because a confident answer from an earlier linker ends the search. A
        prefetch is therefore a hint, never a commitment, and must not be where
        a linker records anything it would not have learned anyway.

        Whatever a call warms replaces what the previous call warmed, so memory
        stays bounded by one window rather than by the length of the run.
        """

        return None

    @classmethod
    @abstractmethod
    async def get_target_bases(cls, config: BaseModel) -> list[str]:
        """
        Returns a list of authority bases that this linker can target.

        Returns
        -------
        List[str]
            A list of authority base identifiers (e.g., "KNAV", "SKC").
        """
        raise NotImplementedError

    @abstractmethod
    async def run(
        self,
        base: str,
        system_number: str,
        record: MarcRecord,
        target_base: str,
    ) -> AuthorityLink | None:
        """
        Attempt to link a catalog record to an authority record.

        Args
        ----
        record:
            The MARC record to analyze for authority linkage.
        base:
            The source catalog base or dataset identifier.
        system_number:
            The system number (identifier) of the record being linked.
        target_base:
            The authority base to link against (e.g., MZK01, KNAV, SKC).

        Returns
        -------
        AuthorityLink | None
            An AuthorityLink instance if a matching authority record is found,
            otherwise None.
        """
        raise NotImplementedError
