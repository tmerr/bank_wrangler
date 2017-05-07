"""
Aggregate transactions across banks.
"""


from bank_wrangler.bank import citizens, fidelity, venmo


def banks():
    return [citizens, fidelity, venmo]
