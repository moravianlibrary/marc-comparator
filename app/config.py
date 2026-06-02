# pragma: exclude file
from datetime import datetime, tzinfo

import pytz
from pydantic import EmailStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CorsConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CORS_")

    allow_origins: list[str] = Field(default=["http://localhost:5173", "http://localhost:8080"])
    allow_credentials: bool = Field(default=True)
    allow_methods: list[str] = Field(default=["*"])
    allow_headers: list[str] = Field(default=["*"])


class PostgresConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POSTGRES_")

    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    database_name: str = Field(default="marc", validation_alias="POSTGRES_DB")
    user: str = Field(default="marcAdmin")
    password: str = Field(default="replaceMe")

    pool_size: int = Field(default=20)
    max_overflow: int = Field(default=0)
    pool_timeout: int = Field(default=30)
    pool_recycle: int = Field(default=1800)

    @property
    def url(self) -> str:
        return (
            f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database_name}"
        )


class BrokerConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BROKER_")

    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0)

    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"


class AdminConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ADMIN_")

    email: EmailStr = Field(default="admin@example.com")
    first_name: str = Field(default="Admin")
    last_name: str = Field(default="User")
    password: str = Field(default="replaceMe")


class AuthConfig(BaseSettings):
    secret_key: str = Field(default="your-secret-key")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=15)
    refresh_token_expire_days: int = Field(default=7)
    cookie_domain: str | None = Field(default=None)
    cookie_secure: bool = Field(default=True)

    admin: AdminConfig = AdminConfig()


class OIDCConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OIDC_")

    enabled: bool = Field(default=False)
    default: bool = Field(default=False)
    issuer_url: str = Field(default="http://localhost:8080/realms/marc-comparator")
    client_id: str = Field(default="marc-comparator")
    client_secret: str = Field(default="")
    app_base_url: str = Field(default="http://localhost:8000")

    @property
    def authorization_endpoint(self) -> str:
        return f"{self.issuer_url}/protocol/openid-connect/auth"

    @property
    def token_endpoint(self) -> str:
        return f"{self.issuer_url}/protocol/openid-connect/token"

    @property
    def userinfo_endpoint(self) -> str:
        return f"{self.issuer_url}/protocol/openid-connect/userinfo"

    @property
    def redirect_uri(self) -> str:
        return f"{self.app_base_url}/api/auth/oidc/callback"


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_host: str = Field(default="127.0.0.1")
    app_port: int = Field(default=8000)
    cors: CorsConfig = CorsConfig()

    timezone_name: str = Field(default="Europe/Prague")
    log_level: str = Field(default="info")

    postgres: PostgresConfig = PostgresConfig()
    broker: BrokerConfig = BrokerConfig()
    auth: AuthConfig = AuthConfig()
    oidc: OIDCConfig = OIDCConfig()

    index_batch_size: int = Field(default=1000)
    marc_cache_ttl_seconds: int = Field(default=3600, ge=1)

    @property
    def timezone(self) -> tzinfo:
        return pytz.timezone(self.timezone_name)

    @property
    def timestamp(self) -> datetime:
        return datetime.now(tz=self.timezone)


config = AppConfig()
