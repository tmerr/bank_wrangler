import os
from atomicwrites import atomic_write
from collections import namedtuple
from argparse import Namespace
from bank_wrangler import mockio


ProjectFile = namedtuple('ProjectFile', ['name', 'isbinary'])


required_files = Namespace(
    rules = ProjectFile(name='rules', isbinary=False),
    final_rules = ProjectFile(name='final-rules', isbinary=False),
    vault = ProjectFile(name='vault', isbinary=True),
    vault_keys = ProjectFile(name='vault-keys', isbinary=False)
)


def data_file(key):
    return ProjectFile(name=key + '.data', isbinary=False)


class FileIO(object):
    def __init__(self, rootpath):
        assert os.path.isabs(rootpath)
        self.rootpath = rootpath

    def _fullpath(self, filename):
        return os.path.join(self.rootpath, filename)

    def initialize(self, empty_vault):
        for required in vars(required_files).values():
            isvault = required == required_files.vault
            with self.writer(required, overwrite=False) as f:
                if isvault:
                    f.write(empty_vault)
                else:
                    f.truncate()

    def is_initialized(self):
        return all(os.path.exists(self._fullpath(required.name))
                   for required in vars(required_files).values())

    def reader(self, projectfile):
        mode = 'rb' if projectfile.isbinary else 'r'
        return open(self._fullpath(projectfile.name), mode=mode)

    def writer(self, projectfile, overwrite):
        mode = 'wb' if projectfile.isbinary else 'w'
        return atomic_write(self._fullpath(projectfile.name), mode=mode, overwrite=overwrite)


class MockIO(object):
    def __init__(self):
        self.data_store = {}

    def initialize(self, empty_vault):
        for required in vars(required_files).values():
            if required.isbinary:
                io = mockio.PatchedBytesIO()
            else:
                io = mockio.PatchedStringIO()
            self.data_store[required.name] = io

    def is_initialized(self):
        return len(self.data_store) != 0

    def reader(self, projectfile):
        fileobj = self.data_store[projectfile.name]
        return mockio.open_as_reader(fileobj)

    def writer(self, projectfile, overwrite):
        fileobj = self.data_store[projectfile.name]
        return mockio.open_as_writer(fileobj, overwrite=overwrite)


# Superset FileIO and MockIO with convenience functions.
for io in FileIO, MockIO:
    for required in vars(required_files).values():
        def reader(self):
            return io.reader(self, required)
        def writer(self, overwrite):
            return io.writer(self, required, overwrite)
        setattr(io, '{}_reader'.format(required.name), reader)
        setattr(io, '{}_writer'.format(required.name), writer)
    def data_reader(self, key):
        return io.reader(self, data_file(key))
    def data_writer(self, key, overwrite):
        return io.writer(self, data_file(key))
    io.data_reader = data_reader
    io.data_writer = data_writer
