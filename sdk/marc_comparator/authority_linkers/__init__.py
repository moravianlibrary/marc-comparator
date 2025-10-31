from enum import StrEnum
from typing import Type

from ._base import BaseAuthorityLinker
from .knihovny_cz_linker import KnihovnyCZLinker


class AuthorityLinker(StrEnum):
    KnihovnyCz = "knihovny-cz"


AUTHORITY_LINKER_DISPATCHER: dict[
    AuthorityLinker, Type[BaseAuthorityLinker]
] = {
    AuthorityLinker.KnihovnyCz: KnihovnyCZLinker,
}
