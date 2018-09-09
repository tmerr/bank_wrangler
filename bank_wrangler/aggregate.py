"""Aggregate transactions across banks"""


from bank_wrangler.bank import citizens, fidelity, fidelity_visa, venmo


class BankException(Exception):
    """Wraps any issues that are caused by bank implementation details"""


def banks():
    """Get the list of bank modules"""
    return [citizens, fidelity, fidelity_visa, venmo]


def _pick_module(bank_config):
    return next(b for b in banks() if b.name() == bank_config.bank)


def fetch(key, bank_config, iolayer):
    """
    Fetch transaction data into the io layer for a particular bank config

    Raises:
        BankException
    """
    bank = _pick_module(bank_config)
    with iolayer.data_writer(key) as f:
        try:
            bank.fetch(bank_config.fields, f)
        except Exception as e:
            raise BankException from e


def list_transactions(key, config, iolayer):
    """
    Read transaction from the io layer for a particular bank config

    Raises:
        BankException
    """
    bank = _pick_module(config)
    with iolayer.data_reader(key) as f:
        try:
            return bank.transactions(f)
        except Exception as e:
            raise BankException from e


def accounts_by_bank(configs_by_key, iolayer):
    """
    Make a dictionary mapping from bank name to set of accounts.

    Raises:
        BankException
    """
    result = {}
    for key, config in configs_by_key.items():
        with iolayer.data_reader(key) as f:
            try:
                result[config.bank] = _pick_module(config).accounts(f)
            except Exception as e:
                raise BankException from e
    return result
