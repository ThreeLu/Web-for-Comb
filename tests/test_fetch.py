import fetch as F

SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2606.19473v2</id>
    <published>2026-06-17T18:05:33Z</published>
    <title>Vertex cuts and
      median decompositions</title>
    <summary>  We study   median decompositions. </summary>
    <author><name>Joseph P. MacManus</name></author>
    <author><name>Bobby Miraftab</name></author>
    <arxiv:comment>15 pages</arxiv:comment>
    <arxiv:doi>10.1000/x</arxiv:doi>
    <category term="math.PR"/>
    <category term="math.CO"/>
    <arxiv:primary_category term="math.CO"/>
  </entry>
</feed>"""


def test_parse_api_feed_strips_version_and_normalizes():
    meta = F.parse_api_feed(SAMPLE)
    assert set(meta) == {"2606.19473"}          # version suffix stripped
    m = meta["2606.19473"]
    assert m["title"] == "Vertex cuts and median decompositions"  # whitespace collapsed
    assert m["summary"] == "We study median decompositions."
    assert m["authors"] == ["Joseph P. MacManus", "Bobby Miraftab"]
    assert m["published"] == "2026-06-17"        # date only
    assert m["doi"] == "10.1000/x"
    assert m["comment"] == "15 pages"


def test_parse_api_feed_primary_category_first():
    m = F.parse_api_feed(SAMPLE)["2606.19473"]
    assert m["categories"][0] == "math.CO"       # primary first
    assert set(m["categories"]) == {"math.CO", "math.PR"}


def test_parse_listing_extracts_new_submissions():
    html = """
    <h3>New submissions</h3>
    <dl>
      <dt><a href="/abs/2606.00001">arXiv:2606.00001</a></dt>
      <dd><div class="list-title">Title: A nice paper</div>
          <div class="list-authors"><a>Jane Doe</a></div>
          <div class="list-subjects">Subjects: Combinatorics (math.CO)</div></dd>
    </dl>
    <h3>Cross submissions</h3>
    <dl><dt><a href="/abs/2606.99999">x</a></dt><dd>skip</dd></dl>
    """
    papers = F.parse_listing(html)
    assert [p["id"] for p in papers] == ["2606.00001"]   # cross-list excluded
    assert papers[0]["title"] == "A nice paper"
