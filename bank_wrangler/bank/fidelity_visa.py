"""A bank backend for Fidelity Rewards Visa cards."""


from datetime import datetime, timedelta
from decimal import Decimal
import time
import csv
import shutil
import tempfile
from bank_wrangler.bank.common import FirefoxDownloadDriver, fidelity_login
from bank_wrangler.config import ConfigField
from bank_wrangler import schema
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC


# How many months back the server allows us to download transaction data.
ALLOWED_DOWNLOAD_MONTHS = 18


def name():
    return 'Fidelity Visa'


def filename():
    return 'fidelity_visa.csv'


def empty_config():
    return [
        ConfigField(False, 'Username', None),
        ConfigField(True, 'Password', None),
        ConfigField(False, 'Last Four Digits of Credit Card Number', None),
    ]


def _start_date_string(end_date_string):
    """
    Compute the start date for downloading transactions.

    This is a pure function of the default end date which is assumed to be
    today. The reason we don't use datetime.now() to overwrite the default end
    date is to avoid the edge case where we accidentally set a date in the
    future thanks to time zone differences, and the server rejects our request.

    Naively compute the start date by subtracting months using modular
    arithmetic, and always set the day to 1. Since this probably isn't how the
    server computes months, compensate for error by subtracting one less month
    than we ordinarily would.
    """
    month1, day1, year1 = map(int, end_date_string.split('/'))
    time_disagreement = abs(datetime(year1, month1, day1) - datetime.now())
    assert time_disagreement < timedelta(hours=48)
    months_to_subtract = ALLOWED_DOWNLOAD_MONTHS - 1
    delta_years, month0 = divmod(month1 - months_to_subtract, 12)
    assert delta_years <= 0
    if month0 == 0:
        month0 = 12
        delta_years -= 1
    year0 = year1 + delta_years
    day0 = 1
    return f"{month0:0>2}/{day0:0>2}/{year0:0>4}"


def _download(config, tempdir):
    username, password, lastfour = config

    driver = FirefoxDownloadDriver(tempdir, 'application/x-csv')
    driver.get('https://www.fidelity.com')
    fidelity_login(driver, username.value, password.value)

    # Wait for content.
    driver.implicitly_wait(30)
    driver.find_element_by_xpath("//*[contains(text(), 'Your Balance History')]")

    # Choose card from the vertical tabs on the left.
    template = '*[data-acct-name="Fidelity® Rewards Visa Signature"]' \
               '[data-acct-number="{}"]'
    selector = template.format(lastfour.value)
    driver.find_element_by_css_selector(selector).click()

    # Next we want to click the View Transactions link. But clicking it too soon
    # does nothing. Use time.sleep since the other obvious fixes didn't work.
    clickme = WebDriverWait(driver, 30).until(
        EC.visibility_of_element_located((By.ID, 'viewTransactions')))
    time.sleep(1)
    clickme.click()
    WebDriverWait(driver, 30).until(lambda d: len(d.window_handles) == 2)
    driver.close()
    driver.switch_to_window(driver.window_handles[0])
    driver.find_element_by_id('navDownloadTransactionDataAnchor').click()

    # Complete the download form.
    software_format = Select(driver.find_element_by_name('dnldFileType'))
    software_format.select_by_visible_text('Microsoft Excel')
    start_date = driver.find_element_by_id('startDate')
    start_date.clear()
    start_date.send_keys(_start_date_string(
        driver.find_element_by_id('endDate').get_attribute('value')))
    download_elem = driver.find_element_by_name('Download')
    download_elem.click()

    csv_path = driver.grab_download('download.csv', timeout_seconds=30)
    driver.quit()
    return csv_path


def fetch(config, fileobj):
    """
    Fetch transactions for the Visa card specified in the config.

    We start by logging in to fidelity.com, then click through some menus to
    transfer credentials to Elan Financial Services' site fidelityrewards.com,
    where we download transactions for the past 17-18 months in CSV format.
    """
    *_, lastfour = config
    account_name = f'Fidelity Visa {lastfour.value}'
    fileobj.write(account_name + '\n')
    with tempfile.TemporaryDirectory() as tempdir:
        csv_path = _download(config, tempdir)
        with open(csv_path, 'r') as csv_file:
            shutil.copyfileobj(csv_file, fileobj)


def transactions(fileobj):
    account_name = fileobj.readline().rstrip('\n')
    result = schema.TransactionModel(schema.COLUMNS)
    lines = list(csv.reader(fileobj))[1:]
    for date, transaction_type, description, _, signed_amount_str in lines:
        signed_amount = Decimal(signed_amount_str.replace(',', ''))
        frm, to = 'Universe', account_name
        if signed_amount > 0:
            assert transaction_type == 'CREDIT'
        else:
            assert signed_amount < 0
            assert transaction_type == 'DEBIT'
            frm, to = to, frm
        month, day, year = map(int, date.split('/'))
        result.ingest_row(
            schema.String(name()),
            schema.String(frm),
            schema.String(to),
            schema.Date(year, month, day),
            schema.String(description),
            schema.Dollars(signed_amount.copy_abs()))
    return result


def accounts(fileobj):
    return {fileobj.readline().rstrip('\n')}
