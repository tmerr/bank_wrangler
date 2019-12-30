import os
from atomicwrites import atomic_write


class FileIO:
    def __init__(self, rootpath):
        self.rootpath = rootpath
        self.rules_path = os.path.join(rootpath, 'rules')
        self.final_rules_path = os.path.join(rootpath, 'final-rules')

    def rules_reader(self):
        return open(self.rules_path)

    def final_rules_reader(self):
        return open(self.final_rules_path)

    def initialize(self):
        try:
            os.makedirs(self.rootpath)
        except FileExistsError:
            print(f'fatal: "{self.rootpath}" already exists', file=sys.stderr)
            sys.exit(1)

        with atomic_write(self.rules_path, mode='w', overwrite=False) as f:
            f.truncate()
        with atomic_write(self.final_rules_path, mode='w', overwrite=False) as f:
            f.truncate()

    def is_initialized(self):
        return os.path.exists(self.rules_path) and os.path.exists(self.final_rules_path)
