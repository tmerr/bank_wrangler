from bank_wrangler.bank import citizens, fidelity, fidelity_visa, venmo


class BankException(Exception):
    """Wraps any issues that are caused by bank implementation details"""


_all_banks = [citizens, fidelity, fidelity_visa, venmo]


def generate_config():
    """Generate a new bank config."""
    print('bank:')
    banks = aggregate.banks()
    for i, bank in enumerate(_all_banks):
        print(f'  {i}. {bank.name()}')
    selected = None
    while selected is None:
        choice = input('choice: ')
        try:
            selected = banks[int(choice)]
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
        self.path = lambda key: os.path.join(root, key + '.data')
        self.bank =  next(b for b in _all_banks if b.name() == bank_config.bank)
        self.config = config

    def fetch(self):
        """
        Fetch transactions or raise BankException.
        """
        with atomic_write(self.path, mode='w', overwrite=True) as f:
            try:
                self.bank.fetch(self.config.fields, f)
            except Exception as e:
                raise BankException from e

    def transactions(self):
        """
        Read transactions or raise BankException.
        """
        with open(self.path) as f:
            try:
                return self.bank.transactions(f)
            except Exception as e:
                raise BankException from e

    def accounts(self):
        """
        Read accounts or raise BankException.
        """
        with open(self.path) as f:
            try:
                return m.accounts(f)
            except Exception as e:
                raise BankException from e
