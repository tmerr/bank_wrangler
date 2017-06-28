from nose.tools import assert_equals
from bank_wrangler import aggregate, schema


def test_map_rules():
    transactions = schema.TransactionModel(schema.COLUMNS)
    transactions.ingest_row(
        schema.String('testbank'),
        schema.String('accountA'),
        schema.String('accountB'),
        schema.Date(2017, 2, 4),
        schema.String('some description'),
        schema.Dollars('32.14')
    )

    def rules_function(_transaction):
        return {'from': schema.String('accountC')}, {}

    new_transactions, errors = aggregate.map_rules(rules_function,
                                                   transactions)
    assert_equals(len(new_transactions), 1)
    assert_equals(errors, [])
    assert_equals(new_transactions.view_snapshot()[0],
                  (schema.String('testbank'),
                   schema.String('accountC'),
                   schema.String('accountB'),
                   schema.Date(2017, 2, 4),
                   schema.String('some description'),
                   schema.Dollars('32.14')))
