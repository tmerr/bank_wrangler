"""
Read/write bank configuration options into an encrypted vault.
"""


from collections import namedtuple
import rncryptor
import json


# Each bank's config is a list of ConfigFields
ConfigField = namedtuple('ConfigField', ['hidden', 'label', 'value'])


def _update_banks(banks, iolayer):
    """Update the plain text list of configured bank names"""
    text = '\n'.join(sorted(banks))
    with iolayer.bank_names_writer() as f:
        if len(text) == 0:
            f.truncate()
        else:
            f.write(text)


def list(iolayer):
    """List the bank names with configs in the vault"""
    try:
        with iolayer.bank_names_reader() as f:
            return [line.strip() for line in f if line.strip() != '']
    except FileNotFoundError:
        return []


def _encrypt(data, passphrase):
    """Encrypt python object"""
    cryptor = rncryptor.RNCryptor()
    return cryptor.encrypt(json.dumps(data), passphrase)


def _decrypt(encrypted, passphrase):
    """Decrypt python object"""
    cryptor = rncryptor.RNCryptor()
    return json.loads(cryptor.decrypt(encrypted, passphrase))


def _create_vault(passphrase, iolayer):
    encrypted = _encrypt({}, passphrase)
    with iolayer.vault_writer(overwrite=False) as f:
        f.write(encrypted)
    _update_banks([], iolayer)


def get(bank, passphrase, iolayer):
    """Get bank's config from the vault"""
    try:
        with iolayer.vault_reader() as f:
            encrypted = f.read()
    except FileNotFoundError:
        _create_vault(passphrase, iolayer)
        return get(bank, passphrase, iolayer)
    data = _decrypt(encrypted, passphrase)
    result = data[bank]
    # Hack to restore namedtuples lost during serialization
    return [ConfigField(*line) for line in result]


def _mutate_config(passphrase, mutate, iolayer):
    """Higher-order function: decrypt, apply mutation, encrypt"""
    try:
        with iolayer.vault_reader() as f:
            old_encrypted = f.read()
    except FileNotFoundError:
        _create_vault(passphrase, iolayer)
        return _mutate_config(passphrase, mutate, iolayer)
    data = _decrypt(old_encrypted, passphrase)
    mutate(data)
    new_encrypted = _encrypt(data, passphrase)
    with iolayer.vault_writer(overwrite=True) as f:
        f.write(new_encrypted)
    _update_banks(data.keys(), iolayer)


def put(bank, config, passphrase, iolayer):
    """Put bank's config in the vault"""
    def mutate(data):
        data[bank] = config
    _mutate_config(passphrase, mutate, iolayer)


def delete(bank, passphrase, iolayer):
    """Delete bank's config from the vault"""
    def mutate(data):
        del data[bank]
    _mutate_config(passphrase, mutate, iolayer)
