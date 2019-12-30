from atomicwrites import atomic_write
import importlib
import os


rules_boilerplate = """\
from bank_wrangler.schema import Transaction

def pre_stitch(transactions):
    '''transformtion applied before stitching transactions together'''
    result = []
    for t in transactions:
        # example rule.
        # if t.source == 'foo':
        #     t = t._replace(source='bar')
        result.append(t)
    return result

def post_stitch(transactions):
    '''transformation applied after stitching transactions together'''
    result = []
    for t in transactions:
        result.append(t)
    return result
"""


class Rules:
    def __init__(self, root):
        self.root = root

    def write_boilerplate(self):
        path = os.path.join(self.root, 'rules.py')
        with atomic_write(path, mode='w', overwrite=False) as f:
            f.write(rules_boilerplate)

    def exists(self):
        return os.path.exists(self.root)

    def get_module(self):
        path = os.path.join(self.root, 'rules.py')
        spec = importlib.util.spec_from_file_location('module.name', path)
        rules = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rules)
        return rules
