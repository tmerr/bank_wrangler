"""
Uses OFX to fetch a 3 month window of transactions from Fidelity.

Other possibibilities:
* Download and parse statement PDFs.
  Last 10 years are available, 1 month at a time.
* Download CSVs from Portfolio > Activity & Orders > History > Download.
  Last 5 years are available, 3 months at a time.
"""


from io import BytesIO
from decimal import Decimal
from bank_wrangler.config import ConfigField
from bank_wrangler import schema
from bank_wrangler.bank.common import correct_balance
from ofxtools.Client import OFXClient, InvStmtRq
from ofxtools.Parser import OFXTree


def name():
    return 'Fidelity'


def empty_config():
    return [
        ConfigField(False, 'Username', None),
        ConfigField(True, 'Password', None),
        ConfigField(False, 'Account IDs (Comma Delimited)', None)
    ]


def fetch(config, fileobj):
    username, password, accts = config
    client = OFXClient(
        'https://ofx.fidelity.com/ftgw/OFX/clients/download',
        userid=username.value,
        org='fidelity.com', fid='7776', brokerid='fidelity.com')
    accts = accts.value.split(',')
    resp = client.request_statements(
        password.value,
        *[InvStmtRq(acctid=acct) for acct in accts])
    fileobj.write(resp.read().decode())


def _networth(statement):
    for bal in statement.ballist:
        if bal.name == 'Networth':
            return Decimal(bal.value)
    raise ValueError('could not find net worth of {}'.format(statement))


def _parse_ofx(fileobj):
    munged = BytesIO(fileobj.read()
        # fix missing character in ofx header
        .replace('?<OFX>', '?><OFX>')
        .encode('utf-8'))
    parser = OFXTree()
    parser.parse(munged)
    return parser.convert()


def _statement_transactions(st):
    result = []
    acctname = str(st.invacctfrom.acctid)
    for t in st.transactions:
        if hasattr(t, 'total'):
            # ignore investment buy/sell
            continue
        amount = t.trnamt
        frm, to = '', acctname
        if amount < 0:
            frm, to = to, frm
            amount *= -1
        result.append(schema.Transaction(
            frm,
            to,
            schema.Date(t.dtposted.year, t.dtposted.month, t.dtposted.day),
            str(t.memo),
            Decimal(amount),
        ))
    net = _networth(st)
    correct_balance(acctname, net, result)
    return result


def transactions_by_account(fileobj):
    ofx = _parse_ofx(fileobj)
    result = {}
    for st in ofx.statements:
        result[str(st.invacctfrom.acctid)] = _statement_transactions(st)
    return result
