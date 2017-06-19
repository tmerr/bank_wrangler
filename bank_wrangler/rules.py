from decimal import Decimal
import pyparsing as pp
from bank_wrangler import schema, tresult
import operator
from collections import namedtuple, defaultdict
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


def parse(text):
    result = []
    for line in text.splitlines():
        if len(line.strip()) != 0:
            try:
                result.append(
                    tresult.ok(_parser.parseString(line))
                )
            except pp.ParseException as e:
                result.append(
                    tresult.err((e.lineno, e.col, str(e)))
                )
    return result


def type_check_line(columns, ast_line):
    ast_conditions, ast_assignments = [], []
    for left, op, right in ast_line:
        # Make sure columns exist and types line up
        if op in operator_map:
            try:
                t0 = columns[left].entrytype()
            except KeyError:
                error = f'column does not exist: {left}'
                return result.err(error)
            t1 = right.entrytype()

            if t0 != t1:
                error = f'type mistmatch in {columns[left].entrytype()} {op} {right}'
                return result.err(error)

            if op == '~~' and t0 != 'String':
                error = f'~~ operator not supported on {t1} entrytype'
                return result.err(error)

            # Use the column's index instead of name in the type checked AST.
            # Also substitute in the actual comparison function.
            index = list(columns.keys()).index(left)
            ast_conditions.append((index, operator_map[op], right))
        else:
            assert op == '='
            if left != 'category' or right.entrytype() != 'String':
                error = f'type mismatch in {left} {op} {right}'
                return tresult.err(error)
            ast_assignments.append((left, right))

    new_ast = (ast_conditions, ast_assignments)
    return tresult.ok(new_ast)


def parse_and_check(columns, text):
    return [line.map(lambda goodline: type_check_line(columns, goodline))
            for line in parse(text)]


def compile(lines):
    """
    Translate the type checked ast lines into a python function object
    f: transaction -> (env, conflicts)
    """
    oklines = [line.ok for line in lines if line.has_ok()]

    def f(transaction):
        env = {}
        conflicts = defaultdict(set)
        for line in oklines:
            conditions, assignments = line
            if all(binop(transaction[col], literal)
                   for col, binop, literal in conditions):
                for left, right in assignments:
                    if left in env and env[left] != right:
                        conflicts[left].add(right)
                    else:
                        env[left] = right 
        for c in conflicts:
            conflicts[c].add(env[c])
            del env[c]
        return env, dict(conflicts)

    return f
