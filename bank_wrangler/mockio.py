"""
Mock IO as if this was a fresh installation. Use in-memory
file-like objects that raise FileNotFoundError if read before
written to.
"""


from io import StringIO, BytesIO


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
