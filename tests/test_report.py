from decimal import Decimal
import json
from nose.tools import assert_equal
from bank_wrangler import schema, report


def test_generate_data_json():
    transactions = [
        schema.Transaction(
            'bankA',
            'src',
            'dest',
            schema.Date(1940, '3', 26),
            'something',
            Decimal('29.99'),
            'foo',
        ),
    ]
    actual_parsed = json.loads(
        report._generate_data_json(transactions, ['some_account'])
    )
    expected_parsed = {
        'columns': ['bank', 'source', 'to', 'date', 'description',
            'amount', 'category'],
        'transactions': [['bankA', 'src', 'dest', '1940/03/26', 'something', '29.99', 'foo']],
        'accounts': ['some_account'],
    }
    assert_equal(actual_parsed, expected_parsed)
