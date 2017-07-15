import os
from glob import glob
from itertools import chain
from typing import Iterable
import json
import jinja2


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


def _generate_pages(html_path, css_names, js_names):
    env = jinja2.Environment(
        undefined=jinja2.StrictUndefined,
        loader = jinja2.FileSystemLoader(html_path),
        lstrip_blocks=True,
        trim_blocks=True,
    )

    # used by base.html
    env.globals = {
        'cssimports': css_names,
        'jsimports': js_names,
        'pages': [
            {'name': 'Bank Wrangler', 'url': 'index.html'},
            {'name': 'List', 'url': '#'},
            {'name': 'Balance', 'url': 'balance.html'},
            {'name': 'Spending', 'url': '#'},
        ],
    }

    return {filename: env.get_template(filename).render()
            for filename in ['index.html', 'balance.html']}


def generate(transactionmodel, accounts: Iterable[str]):
    """
    Generate a dictionary representing the files to be written for the
    report, where keys are string filenames and values are string
    file contents.
    """
    reportdir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(reportdir, 'html')
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

    css_names = list(map(os.path.basename, css_paths))
    js_names = list(map(os.path.basename, js_paths)) + ['data.js']
    for filename, text in _generate_pages(html_path,
                                          css_names,
                                          js_names).items():
        files[filename] = text

    return files
