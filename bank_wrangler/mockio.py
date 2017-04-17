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


def open_as_writer(obj):
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
        self.bank_names = PatchedStringIO()
        self.vault = PatchedBytesIO()
        self.bank = defaultdict(PatchedStringIO)

    def bank_names_reader(self):
        return open_as_reader(self.bank_names)

    def bank_names_writer(self):
        return open_as_writer(self.bank_names)

    def vault_reader(self):
        return open_as_reader(self.vault)

    def vault_writer(self, overwrite):
        return open_as_writer(self.vault)

    def bank_reader(self, filename):
        return open_as_reader(self.bank[filename])

    def bank_writer(self, filename):
        return open_as_writer(self.bank[filename])
