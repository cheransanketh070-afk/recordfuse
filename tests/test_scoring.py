from recordfuse.models import EntityRecord
from recordfuse.scoring import SimilarityEngine

def test_exact_email_can_match():
    a = EntityRecord("a", "crm", {"name":"Jose","email":"JOSE@example.com","phone":"123"})
    b = EntityRecord("b", "billing", {"name":"José","email":"jose@example.com","phone":"123"})
    d = SimilarityEngine().compare(a, b)
    assert d.status == "match" and d.score > 0.8

def test_conflicting_identifier_is_rejected():
    a = EntityRecord("a", "crm", {"name":"Jose Silva","email":"a@example.com"})
    b = EntityRecord("b", "billing", {"name":"Jose Silva","email":"b@example.com"})
    assert SimilarityEngine().compare(a, b).status == "rejected"

def test_name_alone_is_not_enough():
    a = EntityRecord("a", "crm", {"name":"John Smith"})
    b = EntityRecord("b", "billing", {"name":"John Smith"})
    assert SimilarityEngine().compare(a, b).status == "rejected"
