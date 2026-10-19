"""The parsers every linker reads somebody else's XML through.

lxml happens not to load a document's internal subset by default, so these
call sites were never exposed. That is a default, not a decision, and it is
one upstream has already changed once; these tests make the guarantee the
linkers rely on fail loudly rather than quietly.
"""

from pathlib import Path

import lxml.etree as etree
import pytest
from marc_comparator.authority_linkers._base import safe_xml_parser, safe_xml_pull_parser

XXE = """<?xml version="1.0"?>
<!DOCTYPE record [<!ENTITY stolen SYSTEM "file://{path}">]>
<record xmlns="http://www.loc.gov/MARC21/slim">
  <leader>&stolen;</leader>
</record>
"""


@pytest.fixture
def secret(tmp_path: Path) -> Path:
    path = tmp_path / "secret.txt"
    path.write_text("a password nobody sent us")
    return path


def document(secret: Path) -> bytes:
    return XXE.format(path=secret).encode()


def leader(root: etree._Element) -> str:
    text = root.findtext("{http://www.loc.gov/MARC21/slim}leader")
    return text or ""


def test_the_payload_is_a_live_file_read_against_this_lxml(secret: Path):
    # Without this the rest of the file could pass against a parser that
    # rejects the document for some unrelated reason, or an lxml that has
    # stopped resolving entities everywhere, and nobody would notice.
    greedy = etree.XMLParser(resolve_entities=True)

    assert "a password nobody sent us" in leader(etree.fromstring(document(secret), greedy))


def test_a_whole_document_cannot_read_a_local_file(secret: Path):
    root = etree.fromstring(document(secret), safe_xml_parser())

    assert "a password" not in leader(root)


def test_a_streamed_document_cannot_read_a_local_file(secret: Path):
    parser = safe_xml_pull_parser(events=("end",))
    parser.feed(document(secret))
    parser.close()

    read = [
        element.text or ""
        for _, element in parser.read_events()
        if etree.QName(element).localname == "leader"
    ]

    assert read and all("a password" not in text for text in read)
