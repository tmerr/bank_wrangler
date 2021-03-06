from atomicwrites import atomic_write
import importlib
import os


rules_boilerplate = """\
from bank_wrangler.schema import Transaction

def pre_stitch(transaction):
    '''transformtion applied before stitching transactions together'''
    # example
    # if transaction.source == 'foo':
    #     return transaction._replace(description='bar')
    return transaction

def post_stitch(transaction):
    '''transformation applied after stitching transactions together'''
    return transaction
"""


class Rules:
    def __init__(self, root):
        self.path = os.path.join(root, 'rules.py')

    def write_boilerplate(self):
        with atomic_write(self.path, mode='w', overwrite=False) as f:
            f.write(rules_boilerplate)

    def exists(self):
        return os.path.exists(self.path)

    def get_module(self):
        spec = importlib.util.spec_from_file_location('module.name', self.path)
        rules = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rules)
        return rules
