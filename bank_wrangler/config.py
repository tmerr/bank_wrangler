"""
Read/write bank configurations into an encrypted vault.
"""


from collections import namedtuple
import json
import rncryptor


# Each config is a bank name and a list of ConfigFields.
Config = namedtuple('Config', ['bank', 'fields'])
ConfigField = namedtuple('ConfigField', ['hidden', 'label', 'value'])


def init(passphrase, iolayer):
    """Create empty vault and vault_keys files"""
    encrypted = _encrypt({}, passphrase)
    with iolayer.vault_writer(overwrite=False) as f:
        f.write(encrypted)
    with iolayer.vault_keys_writer(overwrite=False) as f:
        f.truncate()


def ready(iolayer):
    """Return True if the vault and vault_keys files exist"""
    try:
        with iolayer.vault_reader() as f:
            pass
        with iolayer.vault_keys_reader() as f:
            pass
        return True
    except FileNotFoundError:
        return False


def _update_banks(keylist, iolayer):
    """Update the plain text list of keys"""
    text = '\n'.join(sorted(keylist))
    with iolayer.vault_keys_writer(overwrite=True) as f:
        if len(text) == 0:
            f.truncate()
        else:
            f.write(text)


def keys(iolayer):
    """List keys in the vault"""
    with iolayer.vault_keys_reader() as f:
        return [line.strip() for line in f if line.strip() != '']


def _encrypt(data, passphrase):
    """Encrypt python object"""
    cryptor = rncryptor.RNCryptor()
    return cryptor.encrypt(json.dumps(data), passphrase)


def _decrypt(encrypted, passphrase):
    """Decrypt python object"""
    cryptor = rncryptor.RNCryptor()
    return json.loads(cryptor.decrypt(encrypted, passphrase))


def get(key, passphrase, iolayer):
    """Get config from the vault"""
    with iolayer.vault_reader() as f:
        encrypted = f.read()
    data = _decrypt(encrypted, passphrase)
    bank, fields = data[key]
    # Hack to restore namedtuples lost during serialization
    return Config(bank, [ConfigField(*line) for line in fields])


def _mutate_config(passphrase, mutate, iolayer):
    """Higher-order function: decrypt, apply mutation, encrypt"""
    with iolayer.vault_reader() as f:
        old_encrypted = f.read()
    data = _decrypt(old_encrypted, passphrase)
    mutate(data)
    new_encrypted = _encrypt(data, passphrase)
    with iolayer.vault_writer(overwrite=True) as f:
        f.write(new_encrypted)
    _update_banks(data.keys(), iolayer)


def put(key, config, passphrase, iolayer):
    """Put config in the vault"""
    def mutate(data):
        data[key] = config
    _mutate_config(passphrase, mutate, iolayer)


def delete(key, passphrase, iolayer):
    """Delete config from the vault"""
    def mutate(data):
        del data[key]
    _mutate_config(passphrase, mutate, iolayer)
