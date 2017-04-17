from bank_wrangler import rules, schema
from collections import OrderedDict
from nose.tools import assert_equals


def test_parse_success():
    ok0 = rules.parse('hello >= 1992/06/25')[0].ok
    ok1 = rules.parse('hello >= $32.49')[0].ok
    ok2 = rules.parse('hello >= "ayyy sup \\" fam", wat = $30.25')[0].ok


def test_parse_fail_1():
    err0 = rules.parse('hello hello hello')[0].err
    assert len(err0) > 0

    err1 = rules.parse('HJI^&*()%^&&&')[0].err
    assert len(err1) > 0


def test_parse_fail_2():
    text = 'first == "match this", blah blah try to parse me!'
    err0 = rules.parse(text)[0].err
    assert len(err0) > 0


COLUMNS = OrderedDict({
    'first': schema.String,
    'second': schema.Dollars,
})


def test_compile_1():
    text = 'first == "match this", category = "bucket"'
    ast = rules.parse_and_check(COLUMNS, text)
    f = rules.compile(ast)
    transaction = [
        schema.String('match this'),
        schema.Dollars('$32.53'),
    ]
    expected = (
        {'category': schema.String('bucket')},
        {},
    )
    assert_equals(f(transaction), expected)


def test_compile_2():
    text = '''
        first == "match this", category = "A"
        second >= $10.24, category = "B"
    '''
    ast = rules.parse_and_check(COLUMNS, text)
    f = rules.compile(ast)
    transaction = [
        schema.String('match this'),
        schema.Dollars('$32.53'),
    ]
    expected = (
        {},
        {'category': {schema.String('A'), schema.String('B')}},
    )
    assert f(transaction) == expected


def test_compile_no_match():
    text = '''
        first == "match this", category = "A"
        second >= $10.24, category = "B"
    '''
    ast = rules.parse_and_check(COLUMNS, text)
    f = rules.compile(ast)
    transaction = [
        schema.String('dont match me'),
        schema.Dollars('$0.53'),
    ]
    expected = ({}, {})
    assert f(transaction) == expected
