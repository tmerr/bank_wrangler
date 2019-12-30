from atomicwrites import atomic_write
from bank_wrangler.bank import citizens, fidelity, fidelity_visa, venmo
from bank_wrangler.config import Config
from getpass import getpass
import os


_all_banks = [citizens, fidelity, fidelity_visa, venmo]


def generate_config():
    """Generate a new bank config."""
    print('bank:')
    for i, bank in enumerate(_all_banks):
        print(f'  {i}. {bank.name()}')
    selected = None
    while selected is None:
        choice = input('choice: ')
        try:
            selected = _all_banks[int(choice)]
        except (ValueError, IndexError):
            print('try again')
    fields = []
    for field in selected.empty_config():
        hidden, label, _ = field
        inp = getpass if hidden else input
        value = inp('  {}: '.format(label))
        fields.append(field._replace(value=value))
    return Config(selected.name(), fields)


class BankInstance:
    """An instance of a bank type."""

    def __init__(self, root, key, config):
        self.path = os.path.join(root, key + '.data')
        self.bank =  next(b for b in _all_banks if b.name() == config.bank)
        self.config = config

    def fetch(self):
        with atomic_write(self.path, mode='w', overwrite=True) as f:
            self.bank.fetch(self.config.fields, f)

    def transactions(self):
        with open(self.path) as f:
            return self.bank.transactions(f)

    def accounts(self):
        with open(self.path) as f:
            return self.bank.accounts(f)
