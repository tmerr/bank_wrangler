"""bank_wrangler CLI"""

import sys
import os
from itertools import chain
from getpass import getpass
import click
from bank_wrangler.config import Vault
from bank_wrangler.config import Config
from bank_wrangler.fileio import FileIO
from bank_wrangler import fileio
from bank_wrangler.banks import BankInstance
from bank_wrangler import deduplicate, rules, schema, report


def _assert_initialized():
    if not FileIO(os.getcwd()).is_initialized() or not Vault(os.getcwd()).exists():
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
    iolayer = FileIO(directory)
    iolayer.initialize()
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
    cfg = bank.generate_config()
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


@cli.command()
@click.argument('name')
def fetch(name):
    """Fetch transactions"""
    _assert_initialized()
    iolayer = FileIO(os.getcwd())
    vault = Vault(os.getcwd())
    passphrase = _promptpass()
    try:
        cfg = vault.get(name, passphrase)
    except KeyError:
        print('unknown name ' + name, file=sys.stderr)
        sys.exit(1)
    BankInstance(os.getcwd(), name, cfg).fetch()


@cli.command(name='fetch-all')
def fetch_all():
    """Fetch all transactions"""
    _assert_initialized()
    passphrase = _promptpass()
    iolayer = FileIO(os.getcwd())
    vault = Vault(os.getcwd())
    for name in vault.keys():
        print(f'fetching {name}... ', end='')
        cfg = vault.get(name, passphrase)
        BankInstance(os.getcwd(), name, cfg).fetch()


@cli.command(name='check-rules')
def check_rules():
    """Check rules file for errors"""
    pass


def print_indented(label, errs):
    if len(errs) > 0:
        print('\n{}:'.format(label))
        print('\n'.join('    ' + err for err in errs))


@cli.command(name='list')
@click.argument('name')
def list_transactions(name):
    """List transactions"""
    _assert_initialized()
    iolayer = FileIO(os.getcwd())
    with iolayer.rules_reader() as f:
        parsed, errs = rules.parse(schema.COLUMNS, f.read())
    if len(errs) != 0:
        print_intended('cannot parse rules file', errs)
    passphrase = _promptpass()
    cfg = Vault(os.getcwd()).get(name, passphrase)
    transactions = BankInstance(os.getcwd(), name, cfg).transactions()
    new_transactions, errs = rules.apply(parsed, transactions)
    print(str(new_transactions))
    print_indented('errors while applying rules', errs)


def _list_all_transactions(root, iolayer, passphrase):
    with iolayer.rules_reader() as f:
        parsed1, e1 = rules.parse(schema.COLUMNS_WITH_CATEGORY, f.read())
    if len(e1) != 0:
        print_indented('cannot parse rules file', errs1)
        sys.exit(1)
    with iolayer.final_rules_reader() as f:
        parsed2, e2 = rules.parse(schema.COLUMNS_WITH_CATEGORY, f.read())
    if len(e2) != 0:
        print_indented('cannot parse final rules file', errs1)
        sys.exit(1)
    accounts_by_bank = {}
    transactions0 = schema.TransactionModel(schema.COLUMNS)
    vault = Vault(root)
    for key, conf in vault.get_all():
        for row in BankInstance(root, key, conf).transactions():
            transactions0.ingest_row(*row)
        accounts_by_bank[conf.bank] = BankInstance(root, key, conf).accounts()
    transactions1, errs1 = rules.apply(parsed1, transactions0)
    transactions2 = deduplicate.deduplicate(transactions1, accounts_by_bank)
    transactions3 = schema.TransactionModel(schema.COLUMNS_WITH_CATEGORY)
    for row in transactions2:
        transactions3.ingest_row(*row, schema.String(''))
    transactions4, errs2 = rules.apply(parsed2, transactions3)

    return transactions4, errs1, errs2

@cli.command(name='list-all')
def list_all_transactions():
    """List all transactions"""
    _assert_initialized()
    iolayer = FileIO(os.getcwd())
    passphrase = _promptpass()
    transactions, errs1, errs2 = _list_all_transactions(os.getcwd(), iolayer, passphrase)
    print(str(transactions))
    print_indented('errors while applying rules', errs1)
    print_indented('errors while applying final rules', errs2)


@cli.command(name='report')
def report_cmd():
    _assert_initialized()
    root = os.getcwd()
    iolayer = FileIO(root)
    passphrase = _promptpass()
    accounts = []
    for key, cfg in vault.get_all():
        accounts.extend(BankInstance(root, key, cfg).accounts())
    transactions, errs1, errs2 = _list_all_transactions(os.getcwd(), iolayer, passphrase)
    print_indented('errors while applying rules', errs1)
    print_indented('errors while applying final rules', errs2)
    iolayer.write_report(report.generate(transactions, accounts))


if __name__ == '__main__':
    cli()
