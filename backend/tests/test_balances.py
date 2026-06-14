from uuid import uuid4
from decimal import Decimal
from app.services.balance_engine import calculate_splits, simplify_debts

def test_equal_splits_rounding():
    # Split $10.00 (1000 cents) equally among 3 users
    u1, u2, u3 = uuid4(), uuid4(), uuid4()
    splits = calculate_splits(
        amount_cents=1000,
        split_type="EQUAL",
        participants=[u1, u2, u3],
        share_values=[Decimal("1"), Decimal("1"), Decimal("1")]
    )
    # Sum of splits must be exactly 1000 cents
    assert sum(splits) == 1000
    # First user receives the remainder cent
    assert splits[0] == 334
    assert splits[1] == 333
    assert splits[2] == 333

def test_percentage_splits():
    # Split $15.00 (1500 cents) with 33.33%, 33.33%, 33.34%
    u1, u2, u3 = uuid4(), uuid4(), uuid4()
    splits = calculate_splits(
        amount_cents=1500,
        split_type="PERCENTAGE",
        participants=[u1, u2, u3],
        share_values=[Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]
    )
    assert sum(splits) == 1500
    # 33.33% of 1500 = 499.95 -> 499 cents.
    # 33.34% of 1500 = 500.1 -> 500 cents.
    # Total assigned before remainder correction: 499 + 499 + 500 = 1498.
    # Remainder 2 cents is distributed: first index gets +1, second index gets +1.
    # Yields: splits[0] = 500, splits[1] = 500, splits[2] = 500.
    assert splits == [500, 500, 500]

def test_share_splits():
    # Split $36.00 (3600 cents) in ratio 1:2:1:2 (total = 6 shares)
    u1, u2, u3, u4 = uuid4(), uuid4(), uuid4(), uuid4()
    splits = calculate_splits(
        amount_cents=3600,
        split_type="SHARE",
        participants=[u1, u2, u3, u4],
        share_values=[Decimal("1"), Decimal("2"), Decimal("1"), Decimal("2")]
    )
    assert sum(splits) == 3600
    # 1/6 of 3600 = 600
    # 2/6 of 3600 = 1200
    assert splits[0] == 600
    assert splits[1] == 1200
    assert splits[2] == 600
    assert splits[3] == 1200

def test_simplify_debts():
    # Alice (+5000 cents), Bob (-3000 cents), Charlie (-2000 cents)
    alice = uuid4()
    bob = uuid4()
    charlie = uuid4()

    balances = {
        alice: 5000,
        bob: -3000,
        charlie: -2000
    }

    txs = simplify_debts(balances)
    # Bob should pay Alice 3000 cents
    # Charlie should pay Alice 2000 cents
    assert len(txs) == 2
    
    # Check that net amounts add up correctly
    tx_map = {(t["from_user_id"], t["to_user_id"]): t["amount"] for t in txs}
    assert tx_map.get((bob, alice)) == 3000
    assert tx_map.get((charlie, alice)) == 2000
