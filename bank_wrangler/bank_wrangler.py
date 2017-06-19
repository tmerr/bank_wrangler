"""bank_wrangler CLI"""

import sys
import os
from getpass import getpass
import click
import bank_wrangler.config
from bank_wrangler.config import Config
from bank_wrangler.fileio import FileIO
from bank_wrangler import aggregate


def _assert_initialized():
    iolayer = FileIO(os.getcwd())
    if not bank_wrangler.config.ready(iolayer):
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
    path = os.path.abspath(directory)
    try:
        os.makedirs(path)
    except FileExistsError:
        print(f'fatal: "{path}" already exists', file=sys.stderr)
        sys.exit(1)
    passphrase = getpass('set a master passphrase: ')
    bank_wrangler.config.init(passphrase, FileIO(path))


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


@cli.command(name='list')
@click.argument('name')
def list_transactions(name):
    """List transactions"""
    _assert_initialized()
    iolayer = FileIO(os.getcwd())
    passphrase = _promptpass()
    cfg = bank_wrangler.config.get(name, passphrase, iolayer)
    try:
        print(str(aggregate.list_transactions(name, cfg, iolayer)))
    except aggregate.BankException:
        raise


@cli.command(name='list-all')
def list_all_transactions():
    """List all transactions"""
    _assert_initialized()
    iolayer = FileIO(os.getcwd())
    passphrase = _promptpass()
    configs_by_key = {}
    for key in bank_wrangler.config.keys(iolayer):
        configs_by_key[key] = bank_wrangler.config.get(key, passphrase, iolayer)
    try:
        print(str(aggregate.list_all_transactions(configs_by_key, iolayer)))
    except aggregate.BankException:
        raise


@cli.command()
def show():
    """Visualize data"""
    _assert_initialized()
    #passphrase = _promptpass()


if __name__ == '__main__':
    cli()
