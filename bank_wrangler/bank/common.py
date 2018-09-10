import datetime
import time
import os
from decimal import Decimal
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bank_wrangler import schema


class FirefoxDownloadDriver(webdriver.Firefox):
    def __init__(self, download_dir, *mime_types):
        """
        Create a Firefox webdriver that downloads into the path download_dir,
        and initiates downloads automatically for any of the given MIME types.
        """
        self.download_dir = download_dir
        self.profile = webdriver.FirefoxProfile()
        self.profile.set_preference('browser.helperApps.neverAsk.saveToDisk',
                                    ', '.join(mime_types))

        # Enable setting the default download directory to a custom path.
        self.profile.set_preference('browser.download.folderList', 2)

        self.profile.set_preference('browser.download.dir', self.download_dir)
        super().__init__(self.profile)

    def grab_download(self, filename, timeout_seconds):
        """
        Waits until firefox finishes a download by spinning until `file` exists
        but `path.part` doesn't, then returns the file path or None if we time
        out.
        """
        path = os.path.join(self.download_dir, filename)
        part_path = path + '.part'
        for _ in range(timeout_seconds):
            time.sleep(1)
            if os.path.isfile(path) and not os.path.isfile(part_path):
                return path
        return None


def fidelity_login(driver, username_string, password_string):
    """
    Assumes the driver is either at or loading a Fidelity login form and
    fills it out once it is visible.
    """
    username_elem = WebDriverWait(driver, 30).until(
        EC.visibility_of_element_located((By.ID, 'userId-input')))
    password_elem = driver.find_element_by_id('password')
    username_elem.clear()
    username_elem.send_keys(username_string)
    password_elem.clear()
    password_elem.send_keys(password_string)
    driver.find_element_by_id('fs-login-button').click()


def _oldest_transaction_date(transactions):
    date_column = transactions.columns.index('date')
    if len(transactions) == 0:
        now = datetime.datetime.now()
        return schema.Date(now.year, now.month, now.day)
    return min(t[date_column] for t in transactions)


def compute_balance(account, transactions):
    result = Decimal('0')
    from_column = transactions.columns.index('from')
    to_column = transactions.columns.index('to')
    amount_column = transactions.columns.index('amount')
    for transaction in transactions:
        amount = transaction[amount_column].value
        if transaction[to_column].value == account:
            result += amount
        if transaction[from_column].value == account:
            result -= amount
    return result


def add_balance_correcting_transaction(bankname, account, real_balance, transactions):
    correction = real_balance - compute_balance(account, transactions)
    frm, to = schema.String('Universe'), schema.String(account)
    if correction != 0:
        if correction < 0:
            frm, to = to, frm
            correction *= -1
        transactions.ingest_row(
            schema.String(bankname),
            frm,
            to,
            _oldest_transaction_date(transactions),
            schema.String('Balance correction'),
            schema.Dollars(correction)
        )
    assert real_balance == compute_balance(account, transactions)


def assert_issubset(small, large):
    assert set(small).issubset(large), "{} must be a subset of {}".format(small, large)
