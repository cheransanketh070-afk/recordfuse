import pytest
from recordfuse.models import EntityRecord
from recordfuse.reconcile import Reconciler

def test_reconciliation_merges_and_records_conflict():
    records = [
        EntityRecord("crm-1","crm",{"name":"Jane Doe","email":"jane@example.com","phone":"0400000000"}),
        EntityRecord("bill-9","billing",{"name":"Jane Doe","email":"JANE@example.com","phone":"0400 000 001"}),
        EntityRecord("other-1","support",{"name":"Robert Lee","email":"robert@example.net"}),
    ]
    result = Reconciler().reconcile(records)
    assert result.metrics["clusters"] == 2
    assert result.metrics["conflicts"] == 1
    jane = next(c for c in result.clusters if "crm-1" in c.member_ids)
    assert jane.fields["phone"] == "0400000000"
    assert jane.provenance["phone"] == "crm"

def test_duplicate_ids_fail_fast():
    with pytest.raises(ValueError, match="globally unique"):
        Reconciler().reconcile([
            EntityRecord("x","crm",{"name":"A"}),
            EntityRecord("x","billing",{"name":"B"}),
        ])
