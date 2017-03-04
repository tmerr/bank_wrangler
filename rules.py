from decimal import Decimal
import pyparsing as pp
from PyQt5 import QtCore


RULES_FILE = 'rules.conf'


def build_parser():
    date_literal = pp.Regex(r'(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})') \
                     .setParseAction(lambda s,l,t: (t.year, t.month, t.day))
    dollars_literal = pp.Regex(r'\$\d+(\.\d{2})') \
                        .setParseAction(lambda s,l,t: Decimal(s[l+1:]))
    string_literal = pp.QuotedString('"', escChar='\\') | pp.QuotedString("'", escChar='\\')
    literal = date_literal | dollars_literal | string_literal

    ident = pp.Word(pp.alphas)

    match_op = pp.oneOf(('==', '<=', '>=', '<', '>', '~~'))
    match = ident + match_op + literal

    assign_op = pp.Literal('=')
    assign = ident + assign_op + literal

    part = (match | assign).setParseAction(lambda s,l,t: [t])
    rule = pp.delimitedList(part) + pp.LineEnd()

    return rule


class RulesMonitor():
    def __init__(self):
        self.fs_watcher = QtCore.QFileSystemWatcher([
            '/home/tmerr/code/oss/bank-wrangler',
            '/home/tmerr/code/oss/bank-wrangler/rules.conf',
        ])
        self.fs_watcher.fileChanged.connect(self.on_change)
        self.fs_watcher.directoryChanged.connect(self.on_change)
        self.parser = build_parser()
        self.cached_text = ''

    def on_change(self, path):
        try:
            with open(RULES_FILE, 'r') as f:
                text = f.read()
        except FileNotFoundError as e:
            # When overwriting a file, vim might rename it from file.txt
            # to file.txt~, then write the updated data to a new file.txt,
            # and finally delete the file.txt~ backup. This is good for users
            # since there will always be at least one intact copy of the file
            # even if the computer's unplugged in the middle of the save. We
            # should account for these shenanigans by suppressing any errors
            # if a file doesn't exist for a short period of time.
            return
        except IOError as e:
            # todo: write to log
            raise

        if text == self.cached_text:
            return

        self.cached_text = text

        for line in text.splitlines():
            try:
                parsed = self.parser.parseString(line)
            except pp.ParseException as e:
                print(f"error in {RULES_FILE}:{e.lineno}:{e.col}")
            else:
                print(parsed) # Send this to Qt somehow
