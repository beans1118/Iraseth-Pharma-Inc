"""Pure validation contract tests; run in existing isolated MongoDB test environment."""
import pytest
from modules.inventory.service import receive_delivery, InventoryProblem


def test_rejects_empty_lines_without_writing():
    with pytest.raises(InventoryProblem) as exc:
        receive_delivery([], 'DR-123', 'staff@example.com', 'test-key-12345')
    assert exc.value.status == 400


def test_rejects_invalid_second_line_before_writing():
    with pytest.raises(InventoryProblem) as exc:
        receive_delivery([
            {'product_id':'MED1','lot':'A','expires_on':'2099-01-01','qty':2},
            {'product_id':'MED2','lot':'B','expires_on':'2099-01-01','qty':0},
        ], 'DR-123', 'staff@example.com', 'test-key-12345')
    assert 'Line 2' in str(exc.value)


def test_rejects_expired_stock_as_available():
    with pytest.raises(InventoryProblem) as exc:
        receive_delivery([{'product_id':'MED1','lot':'A','expires_on':'2020-01-01','qty':1}],
                         'DR-123','staff@example.com','test-key-12345')
    assert exc.value.status == 409


def test_rejects_missing_reference():
    with pytest.raises(InventoryProblem) as exc:
        receive_delivery([{'product_id':'MED1','lot':'A','expires_on':'2099-01-01','qty':1}],
                         '', 'staff@example.com','test-key-12345')
    assert exc.value.status == 400
