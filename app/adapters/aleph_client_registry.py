from collections.abc import Mapping

from aleph_nought import AlephClient, AlephConfig, build_aleph_client_map

from catalog_records.models import CatalogSettings


class AlephClientRegistry:
    _client_map: Mapping[str, AlephClient] | None = None

    @classmethod
    def load_from_settings(cls, settings: CatalogSettings) -> None:
        cls._client_map = build_aleph_client_map(
            [AlephConfig(base=config.base, oai=config) for config in settings.clients]
        )

    @classmethod
    def get(cls, base: str) -> AlephClient:
        if cls._client_map is None:
            raise Exception(
                "AlephClientRegistry not initialized. No Aleph configuration was provided."
            )

        if base not in cls._client_map:
            raise Exception(f"Aleph client for base '{base}' not found.")

        return cls._client_map[base]
