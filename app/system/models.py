from typing import List

from pydantic import BaseModel


class AuthorityLinkerInfo(BaseModel):
    name: str
    target_bases: List[str]


class SystemInfo(BaseModel):
    system_version: str
    system_commit: str
    uptime_seconds: float
    available_bases: List[str]
    enabled_authority_linkers: List[AuthorityLinkerInfo]
    enabled_comparators: List[str]
    enabled_validators: List[str]
