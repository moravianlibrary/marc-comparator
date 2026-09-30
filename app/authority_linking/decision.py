"""What the linkers concluded about one record, as a value.

Separate from the task layer because more than one thing reads it: the linking
pass builds a decision, and ``claims`` rewrites one according to what a
cataloguer said. Keeping the types here is what lets the second import the
first without importing the whole pipeline back.
"""

from dataclasses import dataclass

from marc_comparator.authority_linkers import AuthorityLink as SdkAuthorityLink


@dataclass(frozen=True, slots=True)
class Candidate:
    """One record that was weighed, and which linker proposed it.

    ``linker`` is optional because not every candidate comes from one: a
    cataloguer's claim can put a record in front of the pipeline that
    retrieval did not find this pass, and naming a linker for it would credit
    one with a find it did not make. The same reasoning as the null
    ``AuthorityLink.linker`` on a row that records a unanimous silence.
    """

    link: SdkAuthorityLink
    #: The name of the linker that proposed it, which is all the write path
    #: ever wanted — carrying the live instance meant a decision could only be
    #: built where the linkers were loaded, and a decision rebuilt from stored
    #: rows is exactly what applying a claim needs.
    linker: str | None = None


@dataclass(frozen=True, slots=True)
class LinkDecision:
    """What the linkers between them concluded about one record and base."""

    #: The accepted candidate, or nothing where none qualified.
    accepted: Candidate | None
    #: Every candidate any linker handed over, best first and deduplicated by
    #: the record it names, including ``accepted``.
    candidates: list[Candidate]
    #: How many were weighed altogether, across the linkers that answered.
    candidate_count: int
    #: Whether a cataloguer ruled a candidate out of this decision. Read only
    #: to explain an absent answer: "nothing was good enough" and "somebody
    #: said no" are different facts about a record, and only one of them is
    #: worth a linker's attention.
    refused_by_cataloguer: bool = False

    @property
    def below_floor(self) -> bool:
        """Candidates were found and none of them cleared a floor.

        The distinction the table exists to record: this is a rejection, and a
        cataloguer looking for a link the system nearly made should find it,
        where an empty retrieval is nothing to look at.
        """

        return self.accepted is None and bool(self.candidates)

    @classmethod
    def nothing_found(cls) -> "LinkDecision":
        return cls(accepted=None, candidates=[], candidate_count=0)
