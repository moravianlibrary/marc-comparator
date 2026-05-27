from typing import Dict, List, Optional

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
    enabled_validators: List[str]
    kramerius_client_urls: Dict[str, str] = {}


class HealthStatus(BaseModel):
    status: str
    details: Optional[Dict[str, str]] = None
