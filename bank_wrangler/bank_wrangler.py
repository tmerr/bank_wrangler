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
from bank_wrangler import aggregate, deduplicate, rules, schema, report


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


def _select_bank():
    print('bank:')
    banks = aggregate.banks()
    for i, bank in enumerate(banks):
        print(f'  {i}. {bank.name()}')
    selected = None
    while selected is None:
        choice = input('choice: ')
        try:
            selected = banks[int(choice)]
        except (ValueError, IndexError):
            print('try again')
    return selected


def _populate_fields(empty):
    populated = []
    for field in empty:
        hidden, label, _ = field
        inp = getpass if hidden else input
        value = inp('  {}: '.format(label))
        populated.append(field._replace(value=value))
    return populated


@config.command()
@click.argument('name')
def add(name):
    """Add a config"""
    _assert_initialized()
    iolayer = FileIO(os.getcwd())
    vault = Vault(os.getcwd())
    if name in vault.keys():
        print('fatal: config name already in use: {name}')
        sys.exit(1)
    passphrase = _promptpass()
    bank = _select_bank()
    fields = _populate_fields(bank.empty_config())
    cfg = Config(bank.name(), fields)
    vault.put(name, cfg, passphrase)


def _expect_valid_name(name, vault):
    valid_names = vault.keys()
    if not name in valid_names:
        template = 'fatal: config must be one of: {}'
        print(template.format(', '.join(valid_names)), file=sys.stderr)
        sys.exit(1)


@config.command()
@click.argument('name')
def remove(name):
    """Remove a config"""
    _assert_initialized()
    iolayer = FileIO(os.getcwd())
    vault = Vault(os.getcwd())
    _expect_valid_name(name, vault)
    passphrase = _promptpass()
    vault.delete(name, passphrase)


@cli.command()
@click.argument('name')
def fetch(name):
    """Fetch transactions"""
    _assert_initialized()
    iolayer = FileIO(os.getcwd())
    vault = Vault(os.getcwd())
    _expect_valid_name(name, vault)
    passphrase = _promptpass()
    cfg = vault.get(name, passphrase)
    try:
        aggregate.fetch(name, cfg, iolayer)
    except aggregate.BankException:
        raise


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
        try:
            aggregate.fetch(name, cfg, iolayer)
            print('OK')
        except aggregate.BankException:
            print('FAILED')
            raise


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
    try:
        transactions = aggregate.list_transactions(name, cfg, iolayer)
    except aggregate.BankException:
        raise

    new_transactions, errs = rules.apply(parsed, transactions)
    print(str(new_transactions))
    print_indented('errors while applying rules', errs)

def _configs_by_key(passphrase):
    vault = Vault(os.getcwd())
    return {key: vault.get(key, passphrase)
            for key in vault.keys()}


def _list_all_transactions(iolayer, passphrase):
    transactions0 = schema.TransactionModel(schema.COLUMNS)
    configs_by_key = _configs_by_key(passphrase)
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
    try:
        for key, conf in configs_by_key.items():
            for row in aggregate.list_transactions(key, conf, iolayer):
                transactions0.ingest_row(*row)
        accounts_by_bank = aggregate.accounts_by_bank(configs_by_key, iolayer)
        transactions1, errs1 = rules.apply(parsed1, transactions0)
        transactions2 = deduplicate.deduplicate(transactions1, accounts_by_bank)
        transactions3 = schema.TransactionModel(schema.COLUMNS_WITH_CATEGORY)
        for row in transactions2:
            transactions3.ingest_row(*row, schema.String(''))
        transactions4, errs2 = rules.apply(parsed2, transactions3)
    except aggregate.BankException:
        raise

    return transactions4, errs1, errs2

@cli.command(name='list-all')
def list_all_transactions():
    """List all transactions"""
    _assert_initialized()
    iolayer = FileIO(os.getcwd())
    passphrase = _promptpass()
    transactions, errs1, errs2 = _list_all_transactions(iolayer, passphrase)
    print(str(transactions))
    print_indented('errors while applying rules', errs1)
    print_indented('errors while applying final rules', errs2)


@cli.command(name='report')
def report_cmd():
    _assert_initialized()
    iolayer = FileIO(os.getcwd())
    passphrase = _promptpass()
    configs_by_key = _configs_by_key(passphrase, iolayer)
    accounts_by_bank = aggregate.accounts_by_bank(configs_by_key, iolayer)
    accounts = chain(*accounts_by_bank.values())
    transactions, errs1, errs2 = _list_all_transactions(iolayer, passphrase)
    print_indented('errors while applying rules', errs1)
    print_indented('errors while applying final rules', errs2)
    iolayer.write_report(report.generate(transactions, accounts))


if __name__ == '__main__':
    cli()
