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
    #: Subset of enabled_validators whose implementation can turn stored
    #: results into a downloadable repair artifact.
    report_capable_validators: list[str] = []
    #: The enabled comparator's name if it can produce an analysis report,
    #: otherwise None. The client uses this as the report `tool` rather than
    #: assuming a comparator name.
    report_capable_comparator: str | None = None
    kramerius_client_urls: dict[str, str] = {}


class HealthStatus(BaseModel):
    status: str
    details: dict[str, str] | None = None
