import rules
import schema
from collections import OrderedDict


def test_parser_success():
    result0 = rules.parse('hello >= 1992/06/25')
    assert result0.success
    assert result0.ast
    assert result0.error is None

    result1 = rules.parse('hello >= $32.49')
    assert result1.success
    assert result1.ast
    assert result1.error is None

    result2 = rules.parse('hello >= "ayyy sup \\" fam", wat = $30.25')
    assert result2.success
    assert result2.ast
    assert result2.error is None


def test_parser_fail():
    result0 = rules.parse('hello hello hello')
    assert not result0.success
    assert result0.ast is None
    assert len(result0.error) > 0

    result1 = rules.parse('HJI^&*()%^&&&')
    assert not result1.success
    assert result1.ast is None
    assert len(result1.error) > 0


COLUMNS = OrderedDict({
    'first': schema.String,
    'second': schema.Dollars,
})


def test_subclassifier_pass():
    text = 'first == "match this", category = "bucket"'
    ok, classify, err = rules.build_subclassifier(COLUMNS, text)
    assert ok
    transaction = [
        schema.String('match this'),
        schema.Dollars('$32.53'),
    ]
    assert(classify(transaction).value == 'bucket')


def test_subclassifier_fail():
    text = 'first == "match this", blah blah try to parse me!'
    ok, classify, err = rules.build_subclassifier(COLUMNS, text)
    assert not ok
    assert len(err) > 0


def test_classifier_pass():
    text = '''
        first == "match this", category = "A"
        second >= $10.24, category = "B"
    '''
    classify, errors = rules.build_classifier(COLUMNS, text)
    expected = {
        1: schema.String("A"),
        2: schema.String("B"),
    }
    transaction = [
        schema.String('match this'),
        schema.Dollars('$32.53'),
    ]
    assert classify(transaction) == expected


def test_classifier_fail():
    text = '''
        first == "match this", category = "A"
        second >= $10.24, category = "B"
    '''
    classify, errors = rules.build_classifier(COLUMNS, text)
    transaction = [
        schema.String('dont match me'),
        schema.Dollars('$0.53'),
    ]
    assert classify(transaction) == {}
