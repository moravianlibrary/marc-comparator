from typing import Mapping

import yaml
from aleph_nought import AlephClient, AlephConfig, build_aleph_client_map


class AlephClientRegistry:
    _client_map: Mapping[str, AlephClient] | None = None

    @classmethod
    def load_from_config(cls, config_path: str) -> None:
        with open(config_path, "r") as f:
            raw_config = yaml.safe_load(f)

        print(raw_config)
        print(
            [AlephConfig.model_validate(item) for item in raw_config]
            if isinstance(raw_config, list)
            else [AlephConfig.model_validate(raw_config)]
        )
        cls._client_map = build_aleph_client_map(
            [AlephConfig.model_validate(item) for item in raw_config]
            if isinstance(raw_config, list)
            else [AlephConfig.model_validate(raw_config)]
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
