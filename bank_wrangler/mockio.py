"""
Mock IO as if this was a fresh installation. Use in-memory
file-like objects that raise FileNotFoundError if read before
written to.
"""


from io import StringIO, BytesIO
from collections import defaultdict


class PatchedStringIO(StringIO):
    def __init__(self):
        self.exists = False
        StringIO.__init__(self)

    def __exit__(self, *args):
        if self.writer:
            self.truncate()
        self.seek(0)


class PatchedBytesIO(BytesIO):
    def __init__(self):
        self.exists = False
        BytesIO.__init__(self)

    def __exit__(self, *args):
        if self.writer:
            self.truncate()
        self.seek(0)


def open_as_writer(obj, overwrite):
    if obj.exists and not overwrite:
        raise FileExistsError
    obj.writer = True
    if obj.writer:
        obj.exists = True
    return obj


def open_as_reader(obj):
    obj.writer = False
    if not obj.exists:
        raise FileNotFoundError
    return obj


class MockIO(object):
    def __init__(self):
        self.vault_keys = PatchedStringIO()
        self.vault = PatchedBytesIO()
        self.bank = defaultdict(PatchedStringIO)

    def vault_keys_reader(self):
        return open_as_reader(self.vault_keys)

    def vault_keys_writer(self, overwrite):
        return open_as_writer(self.vault_keys, overwrite)

    def vault_reader(self):
        return open_as_reader(self.vault)

    def vault_writer(self, overwrite):
        return open_as_writer(self.vault, overwrite)

    def data_reader(self, key):
        return open_as_reader(self.bank[key])

    def data_writer(self, key):
        return open_as_writer(self.bank[key])

    def data_exists(self, key):
        return key in self.bank
