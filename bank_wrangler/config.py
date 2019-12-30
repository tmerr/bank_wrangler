"""
Read/write bank configurations into an encrypted vault.
"""


from atomicwrites import atomic_write
from collections import namedtuple
import os
import json
import rncryptor


# Each config is a bank name and a list of ConfigFields.
Config = namedtuple('Config', ['bank', 'fields'])
ConfigField = namedtuple('ConfigField', ['hidden', 'label', 'value'])


def _encrypt(data, passphrase):
    """Encrypt python object"""
    cryptor = rncryptor.RNCryptor()
    return cryptor.encrypt(json.dumps(data), passphrase)


def _decrypt(encrypted, passphrase):
    """Decrypt python object"""
    cryptor = rncryptor.RNCryptor()
    return json.loads(cryptor.decrypt(encrypted, passphrase))


class Vault:
    def __init__(self, root):
        self.keys_path = os.path.join(root, 'vault-keys')
        self.store = os.path.join(root, 'vault')

    def exists(self):
        return os.path.exists(self.keys_path) and os.path.exists(self.store)

    def write_empty(self, passphrase):
        with atomic_write(self.keys_path, mode='w', overwrite=False) as f:
            f.truncate()
        with atomic_write(self.store, mode='wb', overwrite=False) as f:
            f.write(_encrypt({}, passphrase))

    def keys(self):
        with open(self.keys_path) as f:
            return [line.strip() for line in f if line.strip() != '']

    def _read(self, passphrase):
        with open(self.store, 'rb') as f:
            d = f.read()
        return _decrypt(d, passphrase)

    def _write(self, data, passphrase):
        new_encrypted = _encrypt(data, passphrase)
        with atomic_write(self.store, mode='wb', overwrite=True) as f:
            f.write(new_encrypted)
        with atomic_write(self.keys_path, mode='w', overwrite=True) as f:
            text = '\n'.join(sorted(data.keys()))
            if len(text) == 0:
                f.truncate()
            else:
                f.write(text)

    def get_all(self, passphrase):
        # restores namedtuples that were lost during serialization
        return {
            key: Config(bank, [ConfigField(*line) for line in fields])
            for key, (bank, fields)
            in self._read(passphrase).items()
        }

    def get(self, key, passphrase):
        return self.get_all(passphrase)[key]

    def put(self, key, config, passphrase):
        data = self._read(passphrase)
        data[key] = config
        self._write(data, passphrase)

    def delete(self, key, passphrase):
        data = self._read(passphrase)
        del data[key]
        self._write(data, passphrase)
