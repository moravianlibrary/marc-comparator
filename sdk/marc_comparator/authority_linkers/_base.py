from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar

import lxml.etree as etree
from marcdantic import MarcRecord
from marcdantic.context import MarcContext
from pydantic import BaseModel

from ..comparators import BaseComparator, RecordComparisonResult
from ..harvest import HarvestCapable
from .identity import IdentityConflict


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


# XML arriving from another system is input, not a document to be trusted.
# An `<!ENTITY>` pointing at a local path is how a stranger's MARCXML reads a
# file on this host (CVE-2026-41066, fixed in lxml 6.1.0, which marcdantic's
# `lxml==6.0.0` pin keeps us off). lxml does not load a document's internal
# subset unless asked, so the parsers below were not exposed even before this
# — but that safety was a default rather than a decision, and `lxml.etree`
# reads the file the moment anything passes `resolve_entities=True`. Nothing
# we parse, a union catalogue's response or a library's published dump, has
# any business declaring an entity or reaching the network to resolve one, so
# every parse in this package says so outright.


def safe_xml_parser() -> etree.XMLParser:
    """A parser for a whole document somebody else wrote."""

    return etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)


def safe_xml_pull_parser(events: tuple[str, ...]) -> etree.XMLPullParser:
    """The same, for a document read as it arrives rather than all at once."""

    return etree.XMLPullParser(
        events=events, resolve_entities=False, no_network=True, load_dtd=False
    )


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
        An optional match score on the comparator scale, 0 to
        ``MATCH_SCALE_MAX``, where bigger is a closer match.
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

    #: *Which* identifier found it, where the route was ``Identifier``.
    #:
    #: The route only says the two records share one of several kinds, and
    #: they are not equally good evidence. A shared national bibliography
    #: number makes a low-scoring pair a finding worth acting on; a shared
    #: ISSN makes the same score mean two issues of one serial, and a shared
    #: ISBN can mean two editions bound together. A cataloguer cannot judge a
    #: low score without it, and neither can a floor.
    #:
    #: A plain string, because the kinds a linker can retrieve by are its own
    #: business — this class does not enumerate somebody else's catalogue.
    matched_identifier: str | None = None

    #: Why this pair cannot be the same work, where anything says so.
    #:
    #: Carried on the candidate rather than applied by the linker alone,
    #: because a vetoed candidate is still worth handing over: the record ends
    #: up saying "this is what was found and this is why it was refused",
    #: which is the only way a rule set too strict is ever visible. A linker
    #: never accepts one — ``link`` is the best candidate with none of these.
    conflicts: list[IdentityConflict] = field(default_factory=list)


@dataclass(slots=True)
class LinkProposal:
    """Everything one linker concluded about one record and one target base.

    ``run`` used to return the accepted link alone, so a caller could not tell
    a lookup that found nothing from one that found several and liked none of
    them, and the candidates that were scored and set aside were discarded
    before anybody could be shown them. Those are different answers and the
    people fixing records need them apart.

    The three cases are readable off the two fields:

    - ``link`` set — this is the match, and ``candidates`` holds it first.
    - ``link`` unset, ``candidates`` empty — nothing was found to consider.
    - ``link`` unset, ``candidates`` filled — something was found and none of
      it cleared the floor for the route it was found by.
    """

    #: The candidate this linker accepts, or nothing where none qualified.
    link: AuthorityLink | None

    #: Every candidate it is willing to hand over, best first, including
    #: ``link``. Ordered by this linker's own confidence, which is comparable
    #: within one list and not between two: one linker may measure a match
    #: while another asserts a constant for every hit.
    candidates: list[AuthorityLink] = field(default_factory=list)

    #: How many were weighed altogether. Not ``len(candidates)``: a linker may
    #: hand back a shortlist, and the difference is what tells a reader that
    #: "one candidate, chosen" is not the same as "eight, one chosen".
    candidate_count: int = 0

    @classmethod
    def nothing_found(cls) -> "LinkProposal":
        """No candidate was retrieved at all."""

        return cls(link=None, candidates=[], candidate_count=0)


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


class BaseAuthorityLinker[ConfigT: BaseModel](HarvestCapable, ABC):
    """
    Abstract base class for MARC authority linkers.

    Subclasses implement logic to link catalog records to authority records
    based on metadata, identifiers, or heuristics.

    Generic in the configuration it takes, so a linker can say what its own
    config is without widening the base's promise. Written out as
    ``BaseAuthorityLinker[MarcXmlDumpLinkerConfig]``; a linker that needs no
    configuration parameterises on ``BaseModel``. Before this the base said
    ``BaseModel`` everywhere and every subclass narrowed it, which is
    unsound — a caller holding the base type could pass any model — and so
    each one had to suppress the override.
    """

    #: The model this linker is configured with, read off the class by the
    #: host before any instance exists. A ClassVar, so it cannot carry
    #: ``ConfigT`` — the tie between the two is the subclass writing both:
    #: ``class X(BaseAuthorityLinker[XConfig])`` with ``config_model = XConfig``.
    config_model: ClassVar[type[BaseModel] | None] = None

    def __init__(self, config: ConfigT | None = None) -> None:
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
    async def get_target_bases(cls, config: ConfigT) -> list[str]:
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
    ) -> LinkProposal:
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
        LinkProposal
            What this linker concluded: the accepted link if there is one, the
            candidates it weighed, and how many there were. Always a proposal,
            never ``None`` — "found nothing" is
            ``LinkProposal.nothing_found()``, and it is a different answer from
            "found something and rejected it", which callers need to tell apart.

        A lookup that could not be performed raises. Reporting it as a proposal
        with no link would be read as "no match exists", and the host deletes
        links it no longer finds.
        """
        raise NotImplementedError
