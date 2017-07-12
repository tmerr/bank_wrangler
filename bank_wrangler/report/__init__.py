import os
from glob import glob
from itertools import chain
from typing import Iterable
import json


def _jsonify_entry(entry):
    kind = entry.entrytype()
    if kind == 'Date':
        return '{:04}/{:02}/{:02}'.format(*entry.value)
    elif kind == 'String':
        return entry.value
    elif kind == 'Dollars':
        return str(entry.value)
    else:
        raise ValueError


def _generate_data_json(transactionmodel, accounts):
    column_names = list(transactionmodel.columns.keys())
    transactions = [list(map(_jsonify_entry, entries))
                    for entries in transactionmodel.transactions]
    return json.dumps({
        'columns': column_names,
        'transactions': transactions,
        'accounts': accounts
    })


def _generate_index(css_names, js_names, index_template):
    js_template = '<script type="text/javascript" charset="utf8" src="{}"></script>'
    css_template = '<link rel="stylesheet" type="text/css" href="{}">'
    includes = '\n'.join(chain(
        map(js_template.format, js_names),
        map(css_template.format, css_names)
    ))
    return index_template.replace('$INCLUDES$', includes)


def generate(transactionmodel, accounts: Iterable[str]):
    """
    Generate a dictionary representing the files to be written for the
    report, where keys are string filenames and values are string
    file contents.
    """
    reportdir = os.path.dirname(os.path.abspath(__file__))
    css_paths = glob(os.path.join(reportdir, 'libs', '*.css'))
    js_paths = (glob(os.path.join(reportdir, 'libs', '*.js')) +
                glob(os.path.join(reportdir, 'js', '*.js')))

    files = {}
    for path in css_paths + js_paths:
        fname = os.path.basename(path)
        with open(path, 'r') as f:
            files[fname] = f.read()

    files['data.js'] = 'const transactionModel = {};'.format(
        _generate_data_json(transactionmodel, list(accounts))
    )

    with open(os.path.join(reportdir, 'index_template.html')) as f:
        index_template = f.read()
        files['index.html'] = _generate_index(
            map(os.path.basename, css_paths),
            list(map(os.path.basename, js_paths)) + ['data.js'],
            index_template
        )

    return files
