"""
Aggregate transactions across banks.
"""


import sys
from itertools import chain
from datetime import datetime
from bank_wrangler.bank import citizens, fidelity, fidelity_visa, venmo
from bank_wrangler import schema


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


def _transform(transaction, env, columns):
    result = list(transaction)
    for key, val in env.items():
        if key in columns:
            i = columns.index(key)
            result[i] = val
        else:
            print(f'ignoring unknown rule assignment to {key}', sys.stderr)
    return result


def map_rules(rules_function, transactions):
    """
    Map the rules function to every transaction.

    Params:
        rules_function: takes a transaction and returns a tuple (env, conflicts), where
            env: a dict from column names to schema.Entry
            conflicts: a dict from column names to sets of schema.Entry
        transactions: a schema.TransactionModel

    Returns:
        a schema.TransactionModel, and a list of conflict error messages.
    """
    columns = transactions.get_columns()
    result = schema.TransactionModel(columns)
    error_messages = []
    for t in transactions:
        env, conflicts = rules_function(t)
        if conflicts:
            error_messages.append(f'rules conflict: {conflicts}')
        result.ingest_row(*_transform(t, env, columns))
    return result, error_messages


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
