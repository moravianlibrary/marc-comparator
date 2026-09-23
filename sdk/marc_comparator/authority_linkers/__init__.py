from enum import StrEnum

from ._base import AuthorityLink, BaseAuthorityLinker
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
    "KnihovnyCZLinker",
    "MarcXmlDumpLinker",
    "MarcXmlDumpLinkerConfig",
]
