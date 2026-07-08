import xml.dom.minidom as minidom

import make_feed as F


def test_build_item_valid_and_has_reasons():
    p = {
        "id": "2606.00001",
        "title": "A <fancy> & tricky title",
        "abs": "https://arxiv.org/abs/2606.00001",
        "authors": ["Noga Alon"],
        "AI": {"tldr": "一句话总结"},
        "match_reasons": {"keywords": ["Hamilton cycle"], "authors": ["Noga Alon"]},
        "_date": "2026-06-20",
    }
    item = F.build_item(p)
    # Wrapping in a root proves the item is well-formed XML (escaping worked).
    doc = minidom.parseString(f"<root>{item}</root>")
    title = doc.getElementsByTagName("title")[0].firstChild.data
    assert title == "A <fancy> & tricky title"
    desc = doc.getElementsByTagName("description")[0].firstChild.data
    assert "命中" in desc and "Hamilton cycle" in desc


def test_cdata_escapes_terminator():
    # A raw "]]>" inside content must not break the CDATA section: the wrapped
    # value should still parse and round-trip to the original text.
    payload = "evil ]]> payload"
    doc = minidom.parseString(f"<d>{F.cdata(payload)}</d>")
    # The split produces several CDATA/text nodes; concatenating recovers input.
    node = doc.getElementsByTagName("d")[0]
    text = "".join(n.data for n in node.childNodes)
    assert text == payload
