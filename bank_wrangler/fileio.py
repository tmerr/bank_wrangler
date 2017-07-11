import os
import shutil
from atomicwrites import atomic_write


class InitializationMixin(object):
    """Sets up files relying only on read/write functions"""

    def initialize(self, empty_vault):
        for writer in (self.rules_writer,
                       self.final_rules_writer,
                       self.vault_keys_writer):
            with writer(overwrite=False) as f:
                f.truncate()
        with self.vault_writer(overwrite=False) as f:
            f.write(empty_vault)

    def is_initialized(self):
        for reader in (self.rules_reader,
                       self.final_rules_reader,
                       self.vault_reader,
                       self.vault_keys_reader):
            try:
                with reader() as f:
                    pass
            except FileNotFoundError:
                return False
        return True


class FileIO(InitializationMixin):
    def __init__(self, rootpath):
        assert os.path.isabs(rootpath)
        self.rootpath = rootpath

    def _fullpath(self, filename):
        return os.path.join(self.rootpath, filename)

    def rules_reader(self):
        return open(self._fullpath('rules'), 'r')

    def rules_writer(self, overwrite):
        return atomic_write(self._fullpath('rules'), mode='w', overwrite=overwrite)

    def final_rules_reader(self):
        return open(self._fullpath('final-rules'), 'r')

    def final_rules_writer(self, overwrite):
        return atomic_write(self._fullpath('final-rules'), mode='w', overwrite=overwrite)

    def vault_keys_reader(self):
        return open(self._fullpath('vault-keys'), 'r')

    def vault_keys_writer(self, overwrite):
        return atomic_write(self._fullpath('vault-keys'), mode='w', overwrite=overwrite)

    def vault_reader(self):
        return open(self._fullpath('vault'), 'rb')

    def vault_writer(self, overwrite):
        return atomic_write(self._fullpath('vault'), mode='wb', overwrite=overwrite)

    def _datapath(self, key):
        return self._fullpath(key) + '.data'

    def data_reader(self, key):
        return open(self._datapath(key), 'r')

    def data_writer(self, key):
        return atomic_write(self._datapath(key), mode='w', overwrite=True)

    def data_exists(self, key):
        return os.path.exists(self._datapath(key))

    def write_report(self, file_dictionary):
        try:
            shutil.rmtree(os.path.join(self.rootpath, 'report'))
        except FileNotFoundError:
            pass
        os.mkdir(os.path.join(self.rootpath, 'report'))
        for filename, datastring in file_dictionary.items():
            path = os.path.join(self.rootpath, 'report', filename)
            with open(path, 'w') as f:
                f.write(datastring)

    def initialize(self, empty_vault):
        try:
            os.makedirs(self.rootpath)
        except FileExistsError:
            print(f'fatal: "{self.rootpath}" already exists', file=sys.stderr)
            sys.exit(1)
        super().initialize(empty_vault)
