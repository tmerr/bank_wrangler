import os
import sys
import glob
import json
from datetime import datetime
from decimal import Decimal
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver import Firefox
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import title_contains
from bank_wrangler.config import ConfigField
from bank_wrangler.bank.common import compute_balance
from bank_wrangler import schema


def name():
    return 'Venmo'


def empty_config():
    return [
        ConfigField(False, 'Username (no email/phone)', None),
        ConfigField(True, 'Password', None),
    ]


def _firefox_default_profile():
    # reference: http://kb.mozillazine.org/Profile_folder_-_Firefox
    # only tested on linux
    if sys.platform in ('linux', 'linux2'):
        parent = os.path.expanduser('~/.mozilla/firefox/')
    elif sys.platform == 'darwin':
        a = os.path.expanduser('~/Library/Application Support/Firefox/Profiles/')
        b = os.path.expanduser('~/Library/Mozilla/Firefox/Profiles/')
        parent = a if os.path.isdir(a) else b
    else:
        assert sys.platform == 'win32'
        parent = os.path.join(os.getenv('APPDATA'), 'Mozilla', 'Firefox', 'Profiles')
    pattern = os.path.join(parent, '*.default')
    return glob.glob(pattern)[0]


def fetch(config, fileobj):
    user, password = config

    # use the user's regular firefox profile instead of a fresh temporary one.
    # this is to avoid getting fingerprinted as a new device which generates
    # annoying emails and asks for additional info. luckily this profile is
    # cloned into a temporary directory, so we can change preferences without
    # affecting the original copy.
    profile = FirefoxProfile(_firefox_default_profile())
    # disable a json viewer that's enabled by default in firefox 53+.
    profile.set_preference('devtools.jsonview.enabled', False)
    driver = Firefox(profile)
    
    driver.get('https://venmo.com/account/sign-in/')
    user_elem = driver.find_element_by_name('phoneEmailUsername')
    user_elem.clear()
    user_elem.send_keys(user.value)
    password_elem = driver.find_element_by_name('password')
    password_elem.clear()
    password_elem.send_keys(password.value)
    password_elem.send_keys(Keys.RETURN)

    WebDriverWait(driver, 15).until(title_contains('Welcome'))

    params = '?start_date=2009-01-01&end_date={}-01-01'.format(datetime.now().year + 1)
    url = 'https://api.venmo.com/v1/transaction-history' + params
    driver.get(url)

    # validate json and raise ValueError on failure.
    pre = driver.find_element_by_tag_name('pre').text
    json.loads(pre)

    driver.quit()
    fileobj.write('{}\n'.format(user.value))
    fileobj.write(pre)


def transactions_by_account(fileobj):
    result = []
    account = fileobj.readline().rstrip('\n')
    data = json.load(fileobj, parse_float=Decimal)['data']

    # not sure if this is a valid assumption, but i'd rather wait for
    # it to break than introduce maybe dead code for injecting a
    # a starting balance.
    assert data['start_balance'] == 0

    for transaction in data['transactions']:
        date_string, _ = transaction['datetime_created'].split('T')
        date = schema.Date(*map(int, date_string.split('-')))
        if transaction['payment'] is not None:
            a = transaction['payment']['actor']['username']
            b = transaction['payment']['target']['user']['username']
            action = transaction['payment']['action']
            if a == account:
                other = b
                b = ''
            elif b == account:
                other = a
                a = ''
            else:
                assert False
            if action == 'pay':
                from_to = [a, b]
            else:
                assert action == 'charge'
                from_to = [b, a]
        elif transaction['capture'] is not None:
            assert transaction['capture']['authorization']['user']['username'] == account
            transaction['note'] = transaction['capture']['authorization']['descriptor']
            other = transaction['note']
            from_to = [account, '']
        else:
            assert False

        funding = transaction.get('funding_source')
        if funding is not None and funding['name'] != 'Venmo balance':
            assert from_to[0] == account
            result.append(schema.Transaction(
                '',
                account,
                date,
                json.dumps({'other': funding['name'], 'note': 'fund ' + transaction['note']}),
                Decimal(transaction['amount'])))
        result.append(schema.Transaction(
            from_to[0],
            from_to[1],
            date,
            json.dumps({'other': other, 'note': transaction['note']}),
            Decimal(transaction['amount'])))
    assert compute_balance(account, result) == data['end_balance']
    return {account: result}
