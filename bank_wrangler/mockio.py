"""
Mock IO as if this was a fresh installation. Use in-memory
file-like objects that raise FileNotFoundError if read before
written to.
"""


from io import StringIO, BytesIO
from collections import defaultdict
from bank_wrangler.fileio import InitializationMixin


class PatchedStringIO(StringIO):
    def __init__(self):
        self.exists = False
        StringIO.__init__(self)

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


class MockIO(InitializationMixin):
    def __init__(self):
        self.rules = PatchedStringIO()
        self.final_rules = PatchedStringIO()
        self.bank = defaultdict(PatchedStringIO)

    def rules_reader(self):
        return open_as_reader(self.rules)

    def rules_writer(self, overwrite):
        return open_as_writer(self.rules, overwrite)

    def final_rules_reader(self):
        return open_as_reader(self.rules)

    def final_rules_writer(self, overwrite):
        return open_as_writer(self.final_rules, overwrite)

    def data_reader(self, key):
        return open_as_reader(self.bank[key])

    def data_writer(self, key):
        return open_as_writer(self.bank[key])

    def data_exists(self, key):
        return key in self.bank

    def write_report(self, file_dictionary):
        raise NotImplementedError
