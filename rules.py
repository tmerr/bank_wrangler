from decimal import Decimal
import pyparsing as pp
from PyQt5 import QtCore
import schema
import operator
from collections import namedtuple
from functools import lru_cache


RULES_FILE = 'rules.conf'


operator_map = {
    '==': operator.eq,
    '<=': operator.le,
    '>=': operator.ge,
    '<': operator.lt,
    '>': operator.gt,
    '~~': lambda a, b: a.matches(b),
}


def _build_parser():
    date_literal = pp.Regex(r'(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})') \
                     .setParseAction(lambda s,l,t: schema.Date(t.year, t.month, t.day))
    dollars_literal = pp.Regex(r'\$\d+(\.\d{2})') \
                        .setParseAction(lambda s,l,t: schema.Dollars(t[0]))
    string_literal = (pp.QuotedString('"', escChar='\\') | pp.QuotedString("'", escChar='\\')) \
                     .setParseAction(lambda s,l,t: schema.String(t[0]))
    literal = date_literal | dollars_literal | string_literal

    ident = pp.Word(pp.alphas)

    match_op = pp.oneOf(operator_map.keys())
    match = ident + match_op + literal

    assign_op = pp.Literal('=')
    assign = ident + assign_op + literal

    part = (match | assign).setParseAction(lambda s,l,t: [t])
    rule = pp.delimitedList(part) + pp.LineEnd()

    return rule


_parser = _build_parser()


ParseResult = namedtuple('ParseResult', ['success', 'ast', 'error'])
def parse(line):
    """
    A wrapper around the internal parser that never raises exceptions,
    indicating success in the returned ParseResult instead.
    """
    try:
        ast = _parser.parseString(line)
    except pp.ParseException as e:
        error = f"error in {RULES_FILE}:{e.lineno}:{e.col}"
        return ParseResult(False, None, error)
    else:
        return ParseResult(True, ast, None)



TypeCheckResult = namedtuple('TypeCheckResult', ['success', 'error'])
def type_check(columns, rule_ast):
    for left, op, right in rule_ast:
        # Make sure columns exist, make sure types line up
        if op in operator_map:
            try:
                t0 = columns[left].entrytype()
            except KeyError:
                error = f'column does not exist: {left}'
                return TypeCheckResult(False, error)
            t1 = right.entrytype()

            if t0 != t1:
                error = f'type mistmatch in {columns[left].entrytype()} {op} {right}'
                return TypeCheckResult(False, error)

            if op == '~~' and t0 != 'String':
                error = f'~~ operator not supported on {t1} entrytype'
                return TypeCheckResult(False, error)
        else:
            assert op == '='
            if left != 'category' or right.entrytype() != 'String':
                error = f'type mismatch in {left} {op} {right}'
                return TypeCheckResult(False, error)

    return TypeCheckResult(True, None)


def classifier_from_ast(columns, rule_ast):
    """
    Translate the rule AST into an executable function.
    This shouldn't fail provided the ast passed type_check.
    """
    # precompute some variables to close over
    conditions = []
    category = None
    for column, op, literal in rule_ast:
        if op in operator_map:
            column_idx = list(columns.keys()).index(column)
            conditions.append((column_idx, operator_map[op], literal))
        else:
            assert op == '='
            category = literal

    # build classifier function
    def classify(transaction):
        if all(binop(transaction[column_idx], literal)
               for column_idx, binop, literal in conditions):
            return category
        return None

    return classify


ClassifierResult = namedtuple('ClassifierResult', ['success', 'classifier', 'error'])
# TODO: Memoize
def build_subclassifier(columns, text):
    parse_result = parse(text)
    if not parse_result.success:
        return ClassifierResult(False, None, f'parse error: {parse_result.error}')

    check_result = type_check(columns, parse_result.ast)
    if not check_result.success:
        return ClassifierResult(False, None, f'type error: {check_result.error}')

    classifier = classifier_from_ast(columns, parse_result.ast)
    return ClassifierResult(True, classifier, None)


AggregateResult = namedtuple('AggregateResult', ['classifier', 'error_map'])
def build_classifier(columns, text):
    """
    Make a classifier from an entire rules file.

    classifier: the resulting function that maps transactions to categories.
    error_map: dictionary mapping line numbers to error strings. lines may
               fail to be parsed or type checked, in which case they're
               unused in the returned classifier.
    """

    def dummy(transaction):
        return None

    subclassifiers = []
    error_map = {}
    for i, line in enumerate(text.splitlines()):
        line = line.strip()
        if len(line) == 0:
            subclassifiers.append(dummy)
            continue

        result = build_subclassifier(columns, line)
        if result.success:
            subclassifiers.append(result.classifier)
        else:
            subclassifiers.append(dummy)
            error_map[i] = result.error

    def classifier(transaction):
        """Return a dictionary mapping rule line numbers to categories"""
        categories = {}
        for i, c in enumerate(subclassifiers):
            category = c(transaction)
            if category is not None:
                categories[i] = category
        return categories

    return AggregateResult(classifier, error_map)


class RulesMonitor():
    def __init__(self):
        self.fs_watcher = QtCore.QFileSystemWatcher([
            '/home/tmerr/code/oss/bank-wrangler',
            '/home/tmerr/code/oss/bank-wrangler/rules.conf',
        ])
        self.fs_watcher.fileChanged.connect(self.on_change)
        self.fs_watcher.directoryChanged.connect(self.on_change)
        self.cached_text = ''

    def on_change(self, path):
        try:
            with open(RULES_FILE, 'r') as f:
                text = f.read()
        except FileNotFoundError as e:
            # When overwriting a file, vim might rename it from file.txt
            # to file.txt~, then write the updated data to a new file.txt,
            # and finally delete the file.txt~ backup. This is good for users
            # since there will always be at least one intact copy of the file
            # even if the computer's unplugged in the middle of the save. We
            # should account for these shenanigans by suppressing any errors
            # if the file is temporarily missing.
            return
        except IOError as e:
            # todo: write to log
            raise

        if text == self.cached_text:
            return

        self.cached_text = text

        for line in text.splitlines():
            parsed = parse(line)
            if parsed.success:
                print(parsed.ast) # Send this to Qt somehow
            else:
                print(parsed.error)
