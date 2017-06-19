"""The schema for our ingested transaction data."""


from functools import total_ordering
from decimal import Decimal
import re
from collections import OrderedDict
from tabulate import tabulate


@total_ordering
class Entry(object):
    """
    An immutable field in the database.
    """
    def __init__(self, value):
        self.value = value

    @classmethod
    def entrytype(cls):
        return cls.__name__

    def _is_valid_entry(self, other):
        return hasattr(other, 'entrytype') and \
               hasattr(other, 'value')

    def __eq__(self, other):
        if not self._is_valid_entry(other):
            return NotImplemented
        return self.value == other.value

    def __lt__(self, other):
        if not self._is_valid_entry(other):
            return NotImplemented
        return self.value < other.value

    def __hash__(self):
        return self.value.__hash__()


class Date(Entry):
    """
    Dates are formatted YYYY/MM/DD.
    """
    def __init__(self, year, month, day):
        value = (int(year), int(month), int(day))
        super().__init__(value)

    def __str__(self):
        return '{:04}/{:02}/{:02}'.format(*self.value)

    def __repr__(self):
        template = 'Date({!r}, {!r}, {!r})'
        return template.format(*self.value)


class String(Entry):
    """
    Strings can contain any unicode character.
    """
    def __init__(self, value):
        super().__init__(str(value))

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return 'String({!r})'.format(self.value)

    def matches(self, pattern):
        return bool(re.search(pattern, self.value))


class Dollars(Entry):
    """
    Dollar quantities are formatted $\d+(.\d{2})?
    """
    def __init__(self, value):
        value = Decimal(str(value).replace(',', '').lstrip('$'))
        assert value >= 0
        super().__init__(value)

    def __str__(self):
        return '$' + str(self.value)

    def __repr__(self):
        return 'Dollars({!r})'.format(self.value)


class TransactionModel():
    """
    A non-persistent database represented using Python objects,
    used to keep track of the table of transactions using
    data ingested from arbitrary sources.
    """
    def __init__(self, columns):
        self.columns = OrderedDict(columns)
        self.transactions = []

    def clear(self):
        self.transactions = []

    def ingest_row(self, *args):
        """Add a row to the database"""
        if len(args) != len(self.columns):
            raise ValueError(f'Tried to call ingest_row with {len(args)} ' \
                             f'arguments. Expected {len(self.columns)}.')
        for argtype, columntype in zip([a.entrytype() for a in args],
                                       [c.entrytype() for c in self.columns.values()]):
            if argtype != columntype:
                raise ValueError(f'Tried to ingest a field of type ' \
                                 f'{argtype} when we expected {columntype}.')
        self.transactions.append(args)

    def view_snapshot(self):
        """View a snapshot of the underlying table of transactions"""

        # A shallow copy is fine since rows are conceptually immutable.
        return self.transactions[:]

    def __iter__(self):
        return self.transactions.__iter__()

    def __len__(self):
        return len(self.transactions)

    def __str__(self):
        return tabulate(self.transactions, headers=self.columns.keys())

    def __repr__(self):
        template = 'TransactionModel({!r}, {!r})'
        return template.format(self.columns, self.transactions)


# Don't directly refer to this from the core code, to encourage orthogonality.
COLUMNS = OrderedDict((
    ('bank', String),
    ('from', String),
    ('to', String),
    ('date', Date),
    ('description', String),
    ('amount', Dollars),
))
