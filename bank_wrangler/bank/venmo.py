import os
import sys
import glob
import json
from datetime import datetime
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver import Firefox
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import title_contains
from bank_wrangler.config import ConfigField
from bank_wrangler import schema


def name():
    return 'Venmo'


def filename():
    return 'venmo.csv'


def empty_config():
    return [
        ConfigField(False, 'Email, phone, or username', None),
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

    # use the user's regular firefox profile instead of a temporary one.
    # this is to avoid getting fingerprinted as a new device which generates
    # annoying emails and asks for additional info.
    profile = FirefoxProfile(_firefox_default_profile())
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
    fileobj.write(pre)


def transactions(fileobj):
    pass
