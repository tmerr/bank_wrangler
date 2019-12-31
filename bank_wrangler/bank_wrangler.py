"""bank_wrangler CLI"""

import sys
import os
from itertools import chain
from getpass import getpass
import click
from tabulate import tabulate
from bank_wrangler.rules import Rules
from bank_wrangler.config import Vault
from bank_wrangler.config import Config
from bank_wrangler.banks import BankInstance, generate_config
from bank_wrangler import stitch, rules, schema, report


def _assert_initialized():
    root = os.getcwd()
    if not Rules(root).exists() or not Vault(root).exists():
        print("fatal: directory must be initialized with `bank_wrangler init`",
              file=sys.stderr)
        sys.exit(1)


def _promptpass():
    return getpass('master passphrase: ')


@click.group()
def cli():
    """Wrangles banks, what can I say."""
    pass


@cli.command()
@click.argument('directory')
def init(directory):
    """Initialize a new bank_wrangler directory"""
    passphrase = getpass('set a master passphrase: ')
    Rules(directory).write_boilerplate()
    Vault(directory).write_empty(passphrase)


@cli.group()
def config():
    """Configuration subcommands"""
    pass


@config.command(name='list')
def listcmd():
    """List configs"""
    _assert_initialized()
    vault = Vault(os.getcwd())
    print('\n'.join(vault.keys()))


@config.command()
@click.argument('name')
def add(name):
    """Add a config"""
    _assert_initialized()
    vault = Vault(os.getcwd())
    if name in vault.keys():
        print('fatal: config name already in use: ' + name)
        sys.exit(1)
    passphrase = _promptpass()
    cfg = generate_config()
    vault.put(name, cfg, passphrase)


@config.command()
@click.argument('name')
def remove(name):
    """Remove a config"""
    _assert_initialized()
    vault = Vault(os.getcwd())
    passphrase = _promptpass()
    try:
        vault.delete(name, passphrase)
    except KeyError:
        print('unknown name ' + name, file=sys.stderr)
        sys.exit(1)


def _fetch(only_key=None):
    _assert_initialized()
    passphrase = _promptpass()
    vault = Vault(os.getcwd())
    items = vault.get_all(passphrase).items()
    if only_key is not None:
        items = [(k, c) for k, c in items if k == only_key]
        if len(items) == 0:
            print('unknown name ' + key, file=sys.stderr)
            sys.exit(1)
    for name, cfg in items:
        print(f'fetching {name}... ')
        BankInstance(os.getcwd(), name, cfg).fetch()


@cli.command()
@click.argument('name')
def fetch(name):
    """Fetch transactions"""
    _fetch(only_key=name)


@cli.command(name='fetch-all')
def fetch_all():
    """Fetch all transactions"""
    _fetch()


def _list_transactions():
    root = os.getcwd()
    vault = Vault(root)
    _assert_initialized()
    passphrase = _promptpass()
    items = vault.get_all(passphrase).items()
    r = Rules(root).get_module()
    transactions_by_account = {}
    for key, conf in items:
        for account, ts in BankInstance(root, key, conf).transactions_by_account().items():
            if account in transactions_by_account:
                raise ValueError('account {} defined more than once'.format(account))
            transactions_by_account[account] = map(r.pre_stitch, ts)
    transactions = stitch.stitch(transactions_by_account)
    transactions = map(r.post_stitch, transactions)
    return transactions, list(transactions_by_account.keys())


@cli.command(name='list')
def list_transactions():
    """List transactions"""
    transactions = _list_transactions()[0]
    print(tabulate(transactions, headers=schema.Transaction._fields))


@cli.command(name='report')
def report_cmd():
    transactions, accounts = _list_transactions()
    report.generate(os.getcwd(), transactions, accounts)


if __name__ == '__main__':
    cli()
