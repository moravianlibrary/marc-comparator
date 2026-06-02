from pydantic import BaseModel


class AuthorityLinkerInfo(BaseModel):
    name: str
    target_bases: list[str]


class SystemInfo(BaseModel):
    system_version: str
    system_commit: str
    uptime_seconds: float
    configured_bases: list[str]
    authority_bases: list[str]
    enabled_authority_linkers: list[AuthorityLinkerInfo]
    enabled_validators: list[str]
    kramerius_client_urls: dict[str, str] = {}


class HealthStatus(BaseModel):
    status: str
    details: dict[str, str] | None = None
