from bank_wrangler import schema
from decimal import Decimal
from nose.tools import assert_equals


def _build_empty_transactions():
    columns = (
        ('first', schema.Date),
        ('second', schema.String),
        ('third', schema.Dollars),
    )
    model = schema.TransactionModel(columns)
    return model


def test_transactions_ingestion():
    model = _build_empty_transactions()
    model.ingest_row(schema.Date(1920, 3, 25),
                     schema.String('something'),
                     schema.Dollars('3.45'))


def test_transactions_view_snapshot():
    model = _build_empty_transactions()
    snapshot0 = model.view_snapshot()
    model.ingest_row(schema.Date(1920, 3, 25),
                     schema.String('something'),
                     schema.Dollars('3.45'))
    snapshot1 = model.view_snapshot()
    model.ingest_row(schema.Date(2200, 3, 25),
                     schema.String('whatever'),
                     schema.Dollars('6000.00'))
    snapshot2 = model.view_snapshot()

    assert len(snapshot0) == 0
    assert len(snapshot1) == 1
    assert len(snapshot2) == 2


def test_string_matches():
    entry = schema.String('hello world')
    assert entry.matches('ello worl')
    assert not entry.matches('^ello world')
    assert not entry.matches('hello worl$')
    assert entry.matches('^hello world$')
    assert entry.matches('^.ello wo[rld]+$')


def test_string_compare():
    a = schema.String('aaa')
    b = schema.String('aab')
    c = schema.String('baa')
    assert a < b < c
    assert a <= b <= c
    assert c > b > a
    assert c >= b >= a
    assert a == a and b == b and c == c


def test_string_str():
    assert str(schema.String('apple')) == 'apple'


def test_date_compare():
    a = schema.Date(1995, 9, 9)
    b = schema.Date(1999, 2, 2)
    c = schema.Date(2000, 1, 1)
    assert a < b < c
    assert a <= b <= c
    assert c > b > a
    assert c >= b >= a
    assert a == a and b == b and c == c


def test_date_str():
    date = schema.Date(1995, 1, 2)
    assert str(date) == '1995/1/2'


def test_dollars_str():
    dollars = schema.Dollars('152.25')
    assert str(dollars) == '$152.25'


def assert_no_exception(f, *args):
    try:
        f(*args)
    except Exception as e:
        assert False, e


def test_many_str_repr():
    # need unqualified names for eval
    Date, String, Dollars = schema.Date, schema.String, schema.Dollars
    date = Date(2017, 3, 23)
    string = String('hello world')
    dollars = Dollars('123.45')
    for entry in date, string, dollars:
        yield assert_no_exception, str, entry
        yield assert_no_exception, repr, entry
        yield assert_equals, entry, eval(repr(entry))


def test_transactions_str_repr():
    model = _build_empty_transactions()
    model.ingest_row(schema.Date(1920, 3, 25),
                     schema.String('something'),
                     schema.Dollars('3.45'))
    yield assert_no_exception, str, model
    yield assert_no_exception, repr, model
