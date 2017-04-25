"""
Aggregate transactions across banks.
"""


from bank_wrangler.bank import citizens, venmo


def banks():
    return [citizens, venmo]
