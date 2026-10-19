"""How 856 links are judged: whose digital library, and where in it they land."""

import pytest
from kramerius.schemas import KrameriusDocument
from marc_comparator.validators import ValidationResult, ValidityStatus
from marc_comparator.validators.kramerius_links import (
    REPAIR_REASONS,
    KrameriusLinksValidator,
    KrameriusLinksValidatorConfig,
)
from marcdantic import MarcRecord

LEADER = "00000nam a2200000 a 4500"
OURS = "https://www.digitalniknihovna.cz/mzk/uuid/{pid}"
PID = "uuid:95591ddd-8712-4dc1-b8da-e7316e19745c"
ROOT_PID = "uuid:11111111-2222-3333-4444-555555555555"
LINK_TEXT = "Digitalizovaný dokument"


def record_with_links(*urls: str) -> MarcRecord:
    return MarcRecord.model_validate(
        {
            "leader": LEADER,
            "fixed_fields": {
                "001": "001450171",
                "005": "20200101000000.0",
                "008": "200101s2020    xr            000 0 cze d",
            },
            "variable_fields": {
                "856": [
                    {"ind1": "4", "ind2": "1", "subfields": {"u": [u], "y": [LINK_TEXT]}}
                    for u in urls
                ]
            },
        }
    )


def record_with_fields(*fields: dict) -> MarcRecord:
    """A record whose 856s are given whole, link text and all."""

    return MarcRecord.model_validate(
        {
            "leader": LEADER,
            "fixed_fields": {
                "001": "001450171",
                "005": "20200101000000.0",
                "008": "200101s2020    xr            000 0 cze d",
            },
            "variable_fields": {
                "856": [{"ind1": "4", "ind2": "1", "subfields": f} for f in fields]
            },
        }
    )


def doc(pid: str, *, level: int = 0, own_pid_path: str | None = None, model_path="monograph"):
    return KrameriusDocument.model_validate(
        {
            "pid": pid,
            "own_pid_path": own_pid_path or pid,
            "own_model_path": model_path,
            "level": level,
        }
    )


class StubSearch:
    def __init__(self, docs):
        self._docs = docs

    def search(self, query, fl=None):
        return list(self._docs)


def validator(docs=(), **config) -> KrameriusLinksValidator:
    v = KrameriusLinksValidator(KrameriusLinksValidatorConfig(**config))
    v.client.Search = StubSearch(docs)  # type: ignore[assignment]
    return v


def by_reason(results: list[ValidationResult]) -> dict[str | None, ValidationResult]:
    return {r.reason: r for r in results}


class TestOtherOnlineResources:
    @pytest.mark.asyncio
    async def test_another_institutions_link_is_an_observation_not_an_error(self):
        # The same document is often held by several libraries, and the record
        # here carries both its own link and the Academy of Sciences' one. The
        # foreign link is not ours to correct.
        foreign = f"https://kramerius.lib.cas.cz/uuid/{PID}"
        results = await validator([doc(PID)]).run(record_with_links(foreign, OURS.format(pid=PID)))

        found = by_reason(results)
        assert "other_online_resource" in found
        assert found["other_online_resource"].status == ValidityStatus.AdditionalInfo
        # Reported against the field it came from, not floating free.
        assert found["other_online_resource"].target.field_index == 0
        # And never judged as our own link gone wrong.
        assert "non_canonical_url_found" not in found
        assert "non_canonical_url_not_found" not in found

    @pytest.mark.asyncio
    async def test_a_foreign_url_is_not_measured_against_our_format(self):
        # A handle-style NKP link carries no uuid at all. That makes it
        # unreadable to us, not malformed.
        handle = "https://kramerius.nkp.cz/kramerius/handle/ABA001/12261491"
        results = await validator().run(record_with_links(handle))

        found = by_reason(results)
        assert "other_online_resource" in found
        assert "invalid_link_format" not in found

    @pytest.mark.asyncio
    async def test_our_own_host_is_still_held_to_our_format(self):
        results = await validator().run(record_with_links("https://digitalniknihovna.cz/mzk/junk"))

        assert "invalid_link_format" in by_reason(results)

    @pytest.mark.asyncio
    async def test_a_legacy_address_of_ours_is_still_a_link_to_repoint(self):
        # kramerius.mzk.cz is our own former address, so a link there really is
        # our document reached the wrong way — unlike another library's host.
        legacy = f"https://kramerius.mzk.cz/search/handle/{PID}"
        results = await validator([doc(PID)]).run(record_with_links(legacy))

        found = by_reason(results)
        assert "other_online_resource" not in found
        assert {"non_canonical_url_found", "non_canonical_url_not_found"} & set(found)

    @pytest.mark.asyncio
    async def test_another_library_on_the_shared_portal_is_not_ours(self):
        # digitalniknihovna.cz is shared: each library has its own section, so
        # the host alone does not make a link ours. Matching on the host and
        # then on the path is what keeps /nkp/ out.
        theirs = f"https://www.digitalniknihovna.cz/nkp/view/{PID}"
        results = await validator([doc(PID)]).run(record_with_links(theirs))

        found = by_reason(results)
        assert "other_online_resource" in found
        assert "non_canonical_url_found" not in found

    @pytest.mark.asyncio
    async def test_a_lookalike_host_is_not_ours(self):
        results = await validator([doc(PID)]).run(
            record_with_links(f"https://kramerius.mzk.cz.example.com/search/handle/{PID}")
        )

        assert "other_online_resource" in by_reason(results)

    @pytest.mark.asyncio
    async def test_a_mistyped_pid_is_a_bad_url_not_a_missing_document(self):
        # A loose PID pattern reads the typo as a document, fails to find it,
        # and reports link_not_found — which removes the 856. A typo must not
        # cost a cataloguer their link.
        typo = (
            "https://www.digitalniknihovna.cz/mzk/view/uuid:6caa5af0-07a9-11e6-a5b6-005056827e52D"
        )
        results = await validator().run(record_with_links(typo))

        found = by_reason(results)
        assert "invalid_link_format" in found
        assert "link_not_found" not in found
        assert not REPAIR_REASONS & set(found)

    @pytest.mark.asyncio
    async def test_the_owned_hosts_are_configurable(self):
        foreign = f"https://kramerius.lib.cas.cz/uuid/{PID}"
        results = await validator(
            [doc(PID)], own_host_pattern=r"^https?://kramerius\.lib\.cas\.cz"
        ).run(record_with_links(foreign))

        assert "other_online_resource" not in by_reason(results)


class TestNonTopLevelDocuments:
    @pytest.mark.asyncio
    async def test_it_names_the_document_the_link_should_use(self):
        deep = doc(PID, level=1, own_pid_path=f"{ROOT_PID}/{PID}", model_path="periodical/page")
        results = await validator([deep]).run(record_with_links(OURS.format(pid=PID)))

        params = by_reason(results)["non_top_level_document"].params or {}
        assert params["pid"] == PID
        assert params["top_level_pid"] == ROOT_PID

    @pytest.mark.asyncio
    async def test_it_is_reported_against_the_field_that_carries_the_link(self):
        # Without a field index the client renders it as an extra, empty 856 row
        # rather than beside the link it is about.
        deep = doc(PID, level=1, own_pid_path=f"{ROOT_PID}/{PID}", model_path="periodical/page")
        results = await validator([deep]).run(record_with_links(OURS.format(pid=PID)))

        assert by_reason(results)["non_top_level_document"].target.field_index == 0

    @pytest.mark.asyncio
    async def test_the_link_is_left_alone_for_a_person_to_judge(self):
        # Repointing it at the top of the hierarchy was right for a page and
        # wrong for everything else: a volume link is a cataloguer's choice,
        # and where several volumes share a parent the rewrite left the record
        # holding one link twice under different $z. So nothing is rewritten
        # and nothing is dropped — the finding goes to a review CSV.
        deep = doc(PID, level=1, own_pid_path=f"{ROOT_PID}/{PID}", model_path="periodical/page")
        plugin = validator([deep])
        results = await plugin.run(record_with_links(OURS.format(pid=PID)))

        changes = plugin._build_changes(results, REPAIR_REASONS)

        assert changes["modifications"] == []
        assert changes["removals"] == set()
        assert by_reason(results)["non_top_level_document"].status == ValidityStatus.ForReview

    @pytest.mark.asyncio
    async def test_it_is_reported_for_review_rather_than_as_a_known_error(self):
        deep = doc(
            PID, level=1, own_pid_path=f"{ROOT_PID}/{PID}", model_path="monograph/monographunit"
        )
        results = await validator([deep]).run(record_with_links(OURS.format(pid=PID)))

        assert "non_top_level_document" in by_reason(results)


class TestAFieldIsJudgedWhateverItsLinkText:
    """A misspelled $y used to cost the whole field.

    `run` skipped any 856 that had no matching link text and no canonical URL,
    before classifying its $u at all. The link never registered, so the
    document looked absent from the record and a second link to it was
    proposed beside the first — 13 records in one report, and every foreign
    and unreadable link in such a field went unreported too.
    """

    @pytest.mark.asyncio
    async def test_an_older_url_form_still_registers_as_our_link(self):
        plugin = validator([doc(PID)])
        results = await plugin.run(
            record_with_fields(
                {
                    "u": [f"https://www.digitalniknihovna.cz/mzk/view/{PID}"],
                    "y": ["digitalizovaný dokument"],  # lowercase: no match
                }
            )
        )

        found = by_reason(results)
        assert "non_canonical_url_found" in found
        assert "missing_link_in_marc" not in found, "the record already links to this document"

    @pytest.mark.asyncio
    async def test_a_copy_elsewhere_is_still_reported(self):
        results = await validator().run(
            record_with_fields(
                {"u": [f"https://kramerius.lib.cas.cz/uuid/{PID}"], "y": ["Digitální dokument"]}
            )
        )

        assert "other_online_resource" in by_reason(results)

    @pytest.mark.asyncio
    async def test_an_unreadable_url_of_ours_is_still_reported(self):
        results = await validator().run(
            record_with_fields({"u": ["https://www.digitalniknihovna.cz/mzk/junk"], "y": ["NDK"]})
        )

        assert "invalid_link_format" in by_reason(results)

    @pytest.mark.asyncio
    async def test_a_publishers_homepage_is_not_a_digital_library(self):
        # An 856 is also where an e-journal's landing page lives. Without a
        # PID and without link text saying otherwise, it is not a digitised
        # copy and reporting it would bury the ones that are.
        results = await validator().run(
            record_with_fields({"u": ["https://eagri.cz/public/portal/mze/publikace"]})
        )

        assert by_reason(results).keys() == {"no_links_found_or_expected"}


class TestTypedDelimitersAndDoubledSchemes:
    """Our own link, mangled, is ours — not another institution's.

    Both shapes come from the same defect: a subfield delimiter that reached
    the catalogue as text. Matched only at the start, the host is missing and
    the link is filed under somebody else's digital library, where nobody
    would go looking for a typo in ours.
    """

    @pytest.mark.asyncio
    async def test_a_doubled_scheme_is_a_typo_in_our_link(self):
        results = await validator().run(
            record_with_links(f"https://https://www.digitalniknihovna.cz/mzk/periodical/{PID}")
        )

        found = by_reason(results)
        assert "invalid_link_format" in found
        assert "other_online_resource" not in found

    @pytest.mark.asyncio
    async def test_a_delimiter_typed_as_text_is_a_typo_in_our_link(self):
        results = await validator().run(record_with_links(f"|u {OURS.format(pid=PID)}"))

        found = by_reason(results)
        assert "invalid_link_format" in found
        assert "other_online_resource" not in found

    @pytest.mark.asyncio
    async def test_a_foreign_url_with_a_scheme_inside_it_stays_foreign(self):
        # A redirector naming its target is somebody else's business.
        results = await validator().run(
            record_with_links(f"https://proxy.example.org/go?to=https://ndk.cz/uuid/{PID}")
        )

        assert "other_online_resource" in by_reason(results)


class TestTheWrittenLinkTextMustBeOneWeAccept:
    def test_a_link_text_our_own_pattern_rejects_is_refused(self):
        plugin = validator(link_text="Digitised document")

        # Harmless until something writes it, so construction only warns.
        assert plugin._config_conflicts
        with pytest.raises(ValueError, match="link_text"):
            plugin.generate_report([])

    def test_the_shipped_defaults_agree(self):
        assert validator()._config_conflicts == []
