"""
Aggregate transactions across banks.
"""


from bank_wrangler.bank import citizens, fidelity, fidelity_visa, venmo


def banks():
    return [citizens, fidelity, fidelity_visa, venmo]
