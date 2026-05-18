import re
from typing import Dict, List

import httpx
from lxml import etree
from marcdantic import MarcRecord
from pydantic import AnyUrl, BaseModel

from ._base import AuthorityLink, BaseAuthorityLinker


class KnihovnyCZBaseMapping(BaseModel):
    base: str
    id_template: str
    pattern: str


class KnihovnyCZLinkerConfig(BaseModel):
    api_url: AnyUrl = "https://www.knihovny.cz/api/v1"

    mappings: List[KnihovnyCZBaseMapping] = [
        KnihovnyCZBaseMapping(
            base="MZK01",
            id_template="mzk.MZK01-{system_number}",
            pattern=r"^mzk\.MZK01-(\d{9})$",
        ),
        KnihovnyCZBaseMapping(
            base="MZK03",
            id_template="mzk.MZK03-{system_number}",
            pattern=r"^mzk\.MZK03-(\d{9})$",
        ),
        KnihovnyCZBaseMapping(
            base="SKC",
            id_template="caslin.SKC01-{system_number}",
            pattern=r"^caslin\.SKC01-(\d{9})$",
        ),
    ]


class KnihovnyCZLinker(BaseAuthorityLinker):
    """
    Authority linker for the Knihovny.cz authority base.
    """

    config_model = KnihovnyCZLinkerConfig

    def __init__(self, config: KnihovnyCZLinkerConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=10)

        self._base_to_id_mapper: Dict[str, str] = {
            mapping.base: mapping.id_template for mapping in config.mappings
        }
        self._id_to_base_patterns: Dict[str, str] = {
            mapping.pattern: mapping.base for mapping in config.mappings
        }

    @classmethod
    async def get_target_bases(
        cls, config: KnihovnyCZLinkerConfig
    ) -> List[str]:
        return [mapping.base for mapping in config.mappings]

    async def _get_dedup_ids(self, id: str):
        response = await self.client.get(
            f"{self.config.api_url}/record",
            params={"id": id, "field[]": "dedupIds"},
        )

        response.raise_for_status()

        return response.json()["records"][0]["dedupIds"]

    async def _get_record(self, id: str) -> MarcRecord | None:
        """
        Fetch the MARC record by its knihovny.cz ID.
        """
        response = await self.client.get(
            f"{self.config.api_url}/record",
            params={"id": id, "field[]": "fullRecord"},
        )

        response.raise_for_status()

        full_record_xml = response.json()["records"][0]["fullRecord"]
        xml_bytes = full_record_xml.encode("utf-8")
        xml_element = etree.fromstring(xml_bytes)

        return MarcRecord.from_xml(xml_element)

    async def run(
        self,
        base: str,
        system_number: str,
        record: MarcRecord,
        target_base: str,
    ) -> AuthorityLink | None:
        if base not in self._base_to_id_mapper:
            raise ValueError(f"Unsupported base: {base}")

        dedup_ids = await self._get_dedup_ids(
            self._base_to_id_mapper[base].format(system_number=system_number)
        )

        target_system_number = None
        for dedup_id in dedup_ids:
            for (
                pattern,
                mapped_base,
            ) in self._id_to_base_patterns.items():
                if target_base != mapped_base:
                    continue

                match_obj = re.match(pattern, dedup_id)
                if not match_obj:
                    continue

                target_system_number = match_obj.group(1)

        if not target_system_number:
            return None

        target_record = await self._get_record(
            self._base_to_id_mapper[target_base].format(
                system_number=target_system_number
            )
        )

        if not target_record:
            raise ValueError(
                f"Record not found for system number: {target_system_number}"
            )

        return AuthorityLink(
            base=target_base,
            system_number=target_system_number,
            record=target_record,
            confidence=1.0,
        )
