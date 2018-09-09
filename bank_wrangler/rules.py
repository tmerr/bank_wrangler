import pyparsing as pp
import operator
from collections import defaultdict
import re
from bank_wrangler import schema


RULES_FILE = 'rules.conf'


operator_map = {
    '==': operator.eq,
    '<=': operator.le,
    '>=': operator.ge,
    '<': operator.lt,
    '>': operator.gt,
    '~~': lambda a, b: re.search(b.value, a.value),
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


def parse_line(columns, lineno, line):
    conditions = []
    assignments = []
    try:
        tokens = _parser.parseString(line)
    except pp.ParseException as e:
        return None, f'parse error at {e.lineno}:{e.col}: {e}'
    for left, op, right in tokens:
        if op in operator_map:
            try:
                t0 = columns[left].entrytype()
            except KeyError:
                error = f'type error at line {lineno}: column does not exist: {left}'
                return None, error
            t1 = right.entrytype()

            if t0 != t1:
                err = f'type error at line {lineno}: type mistmatch in {columns[left].entrytype()} {op} {right}'
                return None, err

            if op == '~~' and t0 != 'String':
                err = f'type error at line {lineno}: ~~ operator not supported on {t1} entrytype'
                return None, err

            index = columns.index(left)
            conditions.append((index, op, right))
        else:
            assert op == '='
            if columns[left].entrytype() != right.entrytype():
                err = f'type error at line {lineno}: type mismatch in {left} {op} {right}'
                return None, err
            assignments.append((left, right))
    return (conditions, assignments), None


def parse(columns, text):
    parsed = []
    errs = []
    for i, line in enumerate(text.splitlines()):
        line = line.strip()
        if len(line) == 0:
            continue
        ok, err = parse_line(columns, i, line)
        if err:
            errs.append(err)
        else:
            parsed.append(ok)
    return parsed, errs


def _apply_one(parsed, transaction, columns, errlog):
    env = {}
    conflicts = defaultdict(set)
    for conditions, assignments in parsed:
        if all(operator_map[binop](transaction[col], literal)
               for col, binop, literal in conditions):
            for left, right in assignments:
                if left in env and env[left] != right:
                    conflicts[left].add(right)
                else:
                    env[left] = right
    for c in conflicts:
        conflicts[c].add(env[c])
        del env[c]
    if conflicts:
        errlog.append(f'rules conflict: {conflicts}')
    result = list(transaction)
    for key, val in env.items():
        if key in columns:
            result[columns.index(key)] = val
        else:
            errlog.append(f'ignoring assignment to unknown column {key}')
    return result


def apply(parsed, transactions):
    """Apply rules to the transactions."""
    errlog = []
    columns = transactions.get_columns()
    result = schema.TransactionModel(columns)
    for t in transactions:
        result.ingest_row(*_apply_one(parsed, t, columns, errlog))
    return result, errlog
