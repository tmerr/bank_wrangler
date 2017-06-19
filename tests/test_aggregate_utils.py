from nose.tools import assert_equals, assert_in
from bank_wrangler import aggregate_utils
from bank_wrangler import schema


def test_deduplicate_ok():
    bank_to_accounts_map = {
        'bankA': ['accountA'],
        'bankB': ['accountB'],
    }

    model = schema.TransactionModel(schema.COLUMNS)
    model.ingest_row(schema.String('bankA'),
                     schema.String('accountA'),
                     schema.String('accountB'),
                     schema.Date(2017, 1, 1),
                     schema.String('a transaction'),
                     schema.Dollars('10.00'))
    model.ingest_row(schema.String('bankB'),
                     schema.String('accountA'),
                     schema.String('accountB'),
                     schema.Date(2017, 1, 1),
                     schema.String('same transaction!'),
                     schema.Dollars('10.00'))

    deduped = aggregate_utils.deduplicate(model, bank_to_accounts_map)

    assert_equals(len(deduped), 1)

    expected = [(
        schema.String('bankA + bankB'),
        schema.String('accountA'),
        schema.String('accountB'),
        schema.Date(2017, 1, 1),
        schema.String('a transaction + same transaction!'),
        schema.Dollars('10.00')
    )]
    assert_equals(deduped.view_snapshot(), expected)


def test_deduplicate_unmatched_missing():
    bank_to_accounts_map = {
        'bankA': ['accountA'],
        'bankB': ['accountB'],
    }
    model = schema.TransactionModel(schema.COLUMNS)
    model.ingest_row(schema.String('bankA'),
                     schema.String('accountA'),
                     schema.String('accountB'),
                     schema.Date(2017, 1, 1),
                     schema.String('a transaction'),
                     schema.Dollars('10.00'))

    deduped = aggregate_utils.deduplicate(model, bank_to_accounts_map)

    expected = [(
        schema.String('bankA'),
        schema.String('accountA'),
        schema.String('unmatched: accountB'),
        schema.Date(2017, 1, 1),
        schema.String('a transaction'),
        schema.Dollars('10.00')
    )]
    assert_equals(deduped.view_snapshot(), expected)


def test_deduplicate_unmatched_typo():
    bank_to_accounts_map = {
        'bankA': ['accountA'],
        'bankB': ['accountB'],
    }

    model = schema.TransactionModel(schema.COLUMNS)
    model.ingest_row(schema.String('bankA'),
                     schema.String('accountA'),
                     schema.String('accountB'),
                     schema.Date(2017, 1, 1),
                     schema.String('a transaction'),
                     schema.Dollars('10.00'))
    model.ingest_row(schema.String('bankB'),
                     schema.String('typo-accountA'),
                     schema.String('accountB'),
                     schema.Date(2017, 1, 1),
                     schema.String('same transaction!'),
                     schema.Dollars('10.00'))

    deduped = aggregate_utils.deduplicate(model, bank_to_accounts_map)
    snapshot = deduped.view_snapshot()
    assert_equals(len(snapshot), 2)

    assert_in((
        schema.String('bankA'),
        schema.String('accountA'),
        schema.String('unmatched: accountB'),
        schema.Date(2017, 1, 1),
        schema.String('a transaction'),
        schema.Dollars('10.00')
    ), snapshot)

    assert_in((
        schema.String('bankB'),
        schema.String('typo-accountA'),
        schema.String('accountB'),
        schema.Date(2017, 1, 1),
        schema.String('same transaction!'),
        schema.Dollars('10.00')
    ), snapshot)


def test_deduplicate_both_unknown():
    bank_to_accounts_map = {
        'bankA': ['accountA'],
        'bankB': ['accountB'],
    }

    model = schema.TransactionModel(schema.COLUMNS)
    model.ingest_row(schema.String('bankA'),
                     schema.String('accountA'),
                     schema.String('unknownB'),
                     schema.Date(2017, 1, 1),
                     schema.String('a transaction'),
                     schema.Dollars('10.00'))
    model.ingest_row(schema.String('bankB'),
                     schema.String('unknownA'),
                     schema.String('accountB'),
                     schema.Date(2017, 1, 1),
                     schema.String('same transaction!'),
                     schema.Dollars('10.00'))

    deduped = aggregate_utils.deduplicate(model, bank_to_accounts_map)
    snapshot = deduped.view_snapshot()
    assert_equals(len(snapshot), 2)

    assert_in((
        schema.String('bankA'),
        schema.String('accountA'),
        schema.String('unknownB'),
        schema.Date(2017, 1, 1),
        schema.String('a transaction'),
        schema.Dollars('10.00')
    ), snapshot)

    assert_in((
        schema.String('bankB'),
        schema.String('unknownA'),
        schema.String('accountB'),
        schema.Date(2017, 1, 1),
        schema.String('same transaction!'),
        schema.Dollars('10.00')
    ), snapshot)
