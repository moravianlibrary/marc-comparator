from typing import Mapping

from aleph_nought import AlephClient, AlephConfig, build_aleph_client_map

from catalog_records.models import CatalogSettings


class AlephClientRegistry:
    _client_map: Mapping[str, AlephClient] | None = None

    @classmethod
    def load_from_settings(cls, settings: CatalogSettings) -> None:
        for config in settings.clients:
            cls._client_map = build_aleph_client_map(
                [AlephConfig.model_validate(item) for item in config]
                if isinstance(config, list)
                else [AlephConfig.model_validate(config)]
            )

    @classmethod
    def get(cls, base: str) -> AlephClient:
        if cls._client_map is None:
            raise Exception(
                "AlephClientRegistry not initialized. "
                "No Aleph configuration was provided."
            )

        if base not in cls._client_map:
            raise Exception(f"Aleph client for base '{base}' not found.")

        return cls._client_map[base]
