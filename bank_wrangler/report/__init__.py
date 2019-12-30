import os
from glob import glob
from itertools import chain
from typing import Iterable
import json
import jinja2
import shutil
from bank_wrangler import schema


def _generate_data_json(transactions, accounts):
    transactions = [list(map(str, row))
                    for row in transactions]
    return json.dumps({
        'columns': schema.Transaction._fields,
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

    pages = {
        'Bank Wrangler': 'index.html',
        'List': 'list.html',
        'Balance': 'balance.html',
        'Spending': 'spending.html',
    }

    # used by base.html
    env.globals = {
        'cssimports': css_names,
        'jsimports': js_names,
        'pages': [{'name': title, 'url': filename}
                  for title, filename in pages.items()],
    }

    return {filename: env.get_template(filename).render(selectedpage=filename)
            for filename in pages.values()}


def generate(root, transactions, accounts: Iterable[str]):
    """Write the report to <root>/report directory."""
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
        _generate_data_json(transactions, list(accounts))
    )

    css_names = list(map(os.path.basename, css_paths))
    js_names = list(map(os.path.basename, js_paths)) + ['data.js']
    for filename, text in _generate_pages(html_path,
                                          css_names,
                                          js_names).items():
        files[filename] = text

    outdir = os.path.join(root, 'report')
    try:
        shutil.rmtree(outdir)
    except FileNotFoundError:
        pass
    os.mkdir(outdir)
    for filename, datastring in files.items():
        path = os.path.join(outdir, filename)
        with open(path, 'w') as f:
            f.write(datastring)
