"""The schema for our ingested transaction data."""


from decimal import Decimal
from functools import total_ordering
from typing import NamedTuple


@total_ordering
class Date:
    """
    Dates are formatted YYYY/MM/DD.
    """
    def __init__(self, year, month, day):
        self.value = (int(year), int(month), int(day))

    def __str__(self):
        return '{:04}/{:02}/{:02}'.format(*self.value)

    def __repr__(self):
        template = 'Date({!r}, {!r}, {!r})'
        return template.format(*self.value)

    def __eq__(self, other):
        return self.value == other.value

    def __lt__(self, other):
        return self.value < other.value

    def __hash__(self):
        return self.value.__hash__()


class Transaction(NamedTuple):
    bank: str
    source: str
    to: str
    date: Date
    description: str
    amount: Decimal
    category: str = 'Unknown'
