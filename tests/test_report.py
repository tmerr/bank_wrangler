import json
from nose.tools import assert_equal
from bank_wrangler import schema, report


def test_generate_data_json():
    columns = (
        ('first', schema.Date),
        ('second', schema.String),
        ('third', schema.Dollars),
    )
    model = schema.TransactionModel(columns)
    model.ingest_row(
        schema.Date(1940, '3', 26),
        schema.String('something'),
        schema.Dollars('29.99')
    )
    actual_parsed = json.loads(
        report._generate_data_json(model, ['some_account'])
    )
    expected_parsed = {
        'columns': [ 'first', 'second', 'third' ],
        'transactions': [['1940/03/26', 'something', '29.99']],
        'accounts': ['some_account'],
    }
    assert_equal(actual_parsed, expected_parsed)
