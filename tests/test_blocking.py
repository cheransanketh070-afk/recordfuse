from recordfuse.blocking import BlockingIndex
from recordfuse.models import EntityRecord

def test_blocking_deduplicates_pairs():
    records = [
        EntityRecord("1","a",{"name":"Jane Doe","email":"jane@example.com"}),
        EntityRecord("2","b",{"name":"Jane Doe","email":"jane@example.com"}),
        EntityRecord("3","c",{"name":"Other Person","email":"other@example.net"}),
    ]
    pairs = BlockingIndex().candidate_pairs(records)
    assert len(pairs) == 1
    assert {pairs[0][0].record_id, pairs[0][1].record_id} == {"1","2"}
