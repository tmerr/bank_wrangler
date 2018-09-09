from bank_wrangler import rules, schema
from bank_wrangler.schema import IndexedOrderedDict
from nose.tools import assert_equals


def check_parse(tc):
    lines, errs = rules.parse(tc['columns'], tc['text'])
    assert len(errs) == tc['want_errs']
    assert len(lines) == tc['want_lines']


def test_parse():
    testcases = [
        {
            'columns': IndexedOrderedDict({'mycolumn': schema.Date}),
            'text': 'mycolumn >= 1992/06/25',
            'want_lines': 1,
            'want_errs': 0,
        },
        {
            'columns': IndexedOrderedDict({'mycolumn': schema.Dollars}),
            'text': 'mycolumn >= $32.49',
            'want_lines': 1,
            'want_errs': 0,
        },
        {
            'columns': IndexedOrderedDict({
                'strcolumn': schema.String,
                'dollarcolumn': schema.Dollars,
            }),
            'text': 'strcolumn >= "ayyy sup \\" fam", dollarcolumn = $30.25',
            'want_lines': 1,
            'want_errs': 0,
        },
        {
            'columns': IndexedOrderedDict({'mycolumn': schema.String}),
            'text': 'hello hello hello',
            'want_lines': 0,
            'want_errs': 1,
        },
        {
            'columns': IndexedOrderedDict({'mycolumn': schema.String}),
            'text': 'HJI^&*()%^&&&',
            'want_lines': 0,
            'want_errs': 1,
        },
        {
            'columns': IndexedOrderedDict({'mycolumn': schema.String}),
            'text': 'first == "match this", blah blah try to parse me!',
            'want_lines': 0,
            'want_errs': 1,
        },
    ]
    for tc in testcases:
        check_parse(tc)


def check_compile(tc):
    got, errlog = rules.apply(tc['parsed'], tc['input'])
    assert list(got) == list(tc['want'])
    assert len(errlog) == tc['want_errs']


def test_compile():
    columns = IndexedOrderedDict({
        'first': schema.String,
        'second': schema.Dollars,
    })
    testcases = [
        {
            'parsed': rules.parse(columns, 'first == "match this", first = "bucket"')[0],
            'input': schema.TransactionModel(
                columns,
                [
                    (schema.String('match this'), schema.Dollars('$32.53')),
                ]),
            'want': schema.TransactionModel(
                columns,
                [
                    (schema.String('bucket'), schema.Dollars('$32.53')),
                ]),
            'want_errs': 0,
        },
        {
            'parsed': rules.parse(columns, '''
                first == "match this", first = "A"
                second >= $10.24, first = "B"
                ''')[0],
            'input': schema.TransactionModel(
                columns,
                [
                    (schema.String('match this'), schema.Dollars('$32.53')),
                ]),
            'want': schema.TransactionModel(
                columns,
                [
                    (schema.String('match this'), schema.Dollars('$32.53')),
                ]),
            'want_errs': 1,
        },
        {
            'parsed': rules.parse(columns, '''
                first == "match this", first = "A"
                second >= $10.24, first = "B"
                ''')[0],
            'input': schema.TransactionModel(
                columns,
                [
                    (schema.String('dont match me'), schema.Dollars('$0.53')),
                ]),
            'want': schema.TransactionModel(
                columns,
                [
                    (schema.String('dont match me'), schema.Dollars('$0.53')),
                ]),
            'want_errs': 0,
        },
    ]
    for tc in testcases:
        check_compile(tc)
