from abc import ABC, abstractmethod
from dataclasses import dataclass

from marcdantic import MarcRecord
from pydantic import BaseModel


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


class BaseAuthorityLinker(ABC):
    """
    Abstract base class for MARC authority linkers.

    Subclasses implement logic to link catalog records to authority records
    based on metadata, identifiers, or heuristics.
    """

    config_model: type[BaseModel] | None = None

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
