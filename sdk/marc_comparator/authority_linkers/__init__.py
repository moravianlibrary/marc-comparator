from enum import StrEnum

from ._base import (
    AuthorityLink,
    BaseAuthorityLinker,
    LinkProposal,
    LinkRequest,
    MatchRoute,
)
from .identity import IdentityConflict, find_identity_conflicts
from .knihovny_cz_linker import KnihovnyCZLinker
from .marcxml_dump_linker import MarcXmlDumpLinker, MarcXmlDumpLinkerConfig


class AuthorityLinker(StrEnum):
    KnihovnyCz = "knihovny-cz"
    MarcXmlDump = "marcxml-dump"


AUTHORITY_LINKER_DISPATCHER: dict[AuthorityLinker, type[BaseAuthorityLinker]] = {
    AuthorityLinker.KnihovnyCz: KnihovnyCZLinker,
    AuthorityLinker.MarcXmlDump: MarcXmlDumpLinker,
}


__all__ = [
    "AuthorityLink",
    "AUTHORITY_LINKER_DISPATCHER",
    "AuthorityLinker",
    "BaseAuthorityLinker",
    "find_identity_conflicts",
    "IdentityConflict",
    "KnihovnyCZLinker",
    "LinkProposal",
    "LinkRequest",
    "MarcXmlDumpLinker",
    "MarcXmlDumpLinkerConfig",
    "MatchRoute",
]
