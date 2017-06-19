import os
from atomicwrites import atomic_write


class FileIO(object):
    def __init__(self, rootpath):
        assert os.path.isabs(rootpath)
        self.rootpath = rootpath

    def _fullpath(self, filename):
        return os.path.join(self.rootpath, filename)

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
