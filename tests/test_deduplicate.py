from decimal import Decimal
from nose.tools import assert_equals, assert_in
from bank_wrangler import deduplicate
from bank_wrangler import schema


def test_deduplicate_ok():
    bank_to_accounts_map = {
        'bankA': ['accountA'],
        'bankB': ['accountB'],
    }

    transactions = [
        schema.Transaction(
            'bankA',
            'accountA',
            'accountB',
             schema.Date(2017, 1, 1),
             'a transaction',
             Decimal('10.00')),
        schema.Transaction(
            'bankB',
            'accountA',
            'accountB',
             schema.Date(2017, 1, 1),
             'same transaction!',
             Decimal('10.00')),
    ]
    deduped = deduplicate.deduplicate(transactions, bank_to_accounts_map)

    assert_equals(len(deduped), 1)

    expected = [
        schema.Transaction(
            'bankA + bankB',
            'accountA',
            'accountB',
            schema.Date(2017, 1, 1),
            'a transaction + same transaction!',
            Decimal('10.00')),
    ]
    assert_equals(deduped, expected)


def test_deduplicate_unmatched_missing():
    bank_to_accounts_map = {
        'bankA': ['accountA'],
        'bankB': ['accountB'],
    }
    transactions = [
        schema.Transaction(
            'bankA',
             'accountA',
             'accountB',
             schema.Date(2017, 1, 1),
             'a transaction',
             Decimal('10.00')),
    ]

    deduped = deduplicate.deduplicate(transactions, bank_to_accounts_map)

    expected = [
        schema.Transaction(
            'bankA',
            'accountA',
            'unmatched: accountB',
            schema.Date(2017, 1, 1),
            'a transaction',
            Decimal('10.00')),
    ]
    assert_equals(deduped, expected)


def test_deduplicate_unmatched_typo():
    bank_to_accounts_map = {
        'bankA': ['accountA'],
        'bankB': ['accountB'],
    }

    transactions = [
        schema.Transaction(
            'bankA',
             'accountA',
             'accountB',
             schema.Date(2017, 1, 1),
             'a transaction',
             Decimal('10.00')),
        schema.Transaction(
            'bankB',
             'typo-accountA',
             'accountB',
             schema.Date(2017, 1, 1),
             'same transaction!',
             Decimal('10.00')),
    ]

    deduped = deduplicate.deduplicate(transactions, bank_to_accounts_map)
    assert_equals(len(deduped), 2)

    assert_in(
        schema.Transaction(
            'bankA',
            'accountA',
            'unmatched: accountB',
            schema.Date(2017, 1, 1),
            'a transaction',
            Decimal('10.00')),
        deduped)

    assert_in(
        schema.Transaction(
            'bankB',
            'typo-accountA',
            'accountB',
            schema.Date(2017, 1, 1),
            'same transaction!',
            Decimal('10.00')),
        deduped)


def test_deduplicate_both_unknown():
    bank_to_accounts_map = {
        'bankA': ['accountA'],
        'bankB': ['accountB'],
    }

    transactions = [
        schema.Transaction(
            'bankA',
            'accountA',
            'unknownB',
             schema.Date(2017, 1, 1),
             'a transaction',
             Decimal('10.00')),
        schema.Transaction(
            'bankB',
             'unknownA',
             'accountB',
             schema.Date(2017, 1, 1),
             'same transaction!',
             Decimal('10.00')),
    ]

    deduped = deduplicate.deduplicate(transactions, bank_to_accounts_map)
    assert_equals(len(deduped), 2)

    assert_in(
        schema.Transaction(
            'bankA',
            'accountA',
            'unknownB',
            schema.Date(2017, 1, 1),
            'a transaction',
            Decimal('10.00')),
        deduped)

    assert_in(
        schema.Transaction(
            'bankB',
            'unknownA',
            'accountB',
            schema.Date(2017, 1, 1),
            'same transaction!',
            Decimal('10.00')),
        deduped)
