class Result(object):
    """
    An object that holds either self.ok or self.err but not both.
    """

    def __init__(self, variant, value):
        if variant == 'ok':
            self.ok = value
        elif variant == 'err':
            self.err = value
        else:
            raise ValueError('variant must be ok or err')

    def has_ok(self):
        return hasattr(self, 'ok')

    def has_err(self):
        return hasattr(self, 'err')

    def map(self, func):
        if self.has_ok():
            return func(self.ok)
        else:
            return self


def ok(value):
    return Result('ok', value)


def err(value):
    return Result('err', value)
