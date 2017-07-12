"""bank_wrangler CLI"""

import sys
import os
from itertools import chain
from getpass import getpass
import click
import bank_wrangler.config
from bank_wrangler.config import Config
from bank_wrangler.fileio import FileIO
from bank_wrangler import fileio
from bank_wrangler import aggregate, deduplicate, rules, schema, report


def _assert_initialized():
    if not FileIO(os.getcwd()).is_initialized():
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
    iolayer = FileIO(os.path.abspath(directory))
    iolayer.initialize(bank_wrangler.config.empty_vault(passphrase))


@cli.group()
def config():
    """Configuration subcommands"""
    pass


@config.command(name='list')
def listcmd():
    """List configs"""
    _assert_initialized()
    print('\n'.join(bank_wrangler.config.keys(FileIO(os.getcwd()))))


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
    valid_names = bank_wrangler.config.keys(iolayer)
    if name in valid_names:
        print('fatal: config name already in use: {name}')
        sys.exit(1)
    passphrase = _promptpass()
    bank = _select_bank()
    fields = _populate_fields(bank.empty_config())
    cfg = Config(bank.name(), fields)
    bank_wrangler.config.put(name, cfg, passphrase, iolayer)


def _expect_valid_name(name, iolayer):
    valid_names = bank_wrangler.config.keys(iolayer)
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
    _expect_valid_name(name, iolayer)
    passphrase = _promptpass()
    bank_wrangler.config.delete(name, passphrase, iolayer)


@cli.command()
@click.argument('name')
def fetch(name):
    """Fetch transactions"""
    _assert_initialized()
    iolayer = FileIO(os.getcwd())
    _expect_valid_name(name, iolayer)
    passphrase = _promptpass()
    cfg = bank_wrangler.config.get(name, passphrase, iolayer)
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
    for name in bank_wrangler.config.keys(iolayer):
        print(f'fetching {name}... ', end='')
        cfg = bank_wrangler.config.get(name, passphrase, iolayer)
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


def _rules_func(iolayer):
    with iolayer.rules_reader() as f:
        text = f.read()
    checked = rules.parse_and_check(schema.COLUMNS, text)
    return rules.compile(checked)


def _final_rules_func(iolayer):
    with iolayer.final_rules_reader() as f:
        text = f.read()
    checked = rules.parse_and_check(schema.COLUMNS_WITH_CATEGORY, text)
    return rules.compile(checked)


@cli.command(name='list')
@click.argument('name')
def list_transactions(name):
    """List transactions"""
    _assert_initialized()
    iolayer = FileIO(os.getcwd())
    passphrase = _promptpass()
    cfg = bank_wrangler.config.get(name, passphrase, iolayer)
    try:
        transactions = aggregate.list_transactions(name, cfg, iolayer)
    except aggregate.BankException:
        raise

    func = _rules_func(iolayer)
    new_transactions, errors = aggregate.map_rules(func, transactions)

    print(str(new_transactions))
    if len(errors) > 0:
        print('\ndetected conflicting rule applications:')
        print('\n'.join('    ' + error for error in errors))


def _configs_by_key(passphrase, iolayer):
    return {key: bank_wrangler.config.get(key, passphrase, iolayer)
            for key in bank_wrangler.config.keys(iolayer)}


@cli.command(name='list-all')
def list_all_transactions():
    """List all transactions"""
    _assert_initialized()
    iolayer = FileIO(os.getcwd())
    passphrase = _promptpass()

    transactions0 = schema.TransactionModel(schema.COLUMNS)

    try:
        for key, conf in _configs_by_key(passphrase, iolayer).items():
            for row in aggregate.list_transactions(key, conf, iolayer):
                transactions0.ingest_row(*row)
        accounts_by_bank = aggregate.accounts_by_bank(configs_by_key, iolayer)
        transactions1, errors1 = aggregate.map_rules(_rules_func(iolayer), transactions0)
        transactions2 = deduplicate.deduplicate(transactions1, accounts_by_bank)
        transactions3, errors2 = aggregate.map_rules(_final_rules_func(iolayer), transactions2)
    except aggregate.BankException:
        raise

    print(str(transactions3))
    if len(errors1) > 0:
        print('\ndetected conflicting rule applications:')
        print('\n'.join('    ' + error for error in errors1))

    if len(errors2) > 0:
        print('\ndetected conflicting rule applications:')
        print('\n'.join('    ' + error for error in errors2))


@cli.command(name='report')
def report_cmd():
    _assert_initialized()
    iolayer = FileIO(os.getcwd())
    passphrase = _promptpass()

    configs_by_key = _configs_by_key(passphrase, iolayer)
    transactions = schema.TransactionModel(schema.COLUMNS)
    try:
        for key, conf in _configs_by_key(passphrase, iolayer).items():
            for row in aggregate.list_transactions(key, conf, iolayer):
                transactions.ingest_row(*row)
    except aggregate.BankException:
        raise
    accounts_by_bank = aggregate.accounts_by_bank(configs_by_key, iolayer)
    accounts = chain(*accounts_by_bank.values())
    iolayer.write_report(report.generate(transactions, accounts))


if __name__ == '__main__':
    cli()
