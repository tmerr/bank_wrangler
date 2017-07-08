"""
A bank backend that fetches transactions from Fidelity's Full View page.

Full View is a free opt-in feature that is managed by Yodlee.  It definitely
lists transactions for Cash Management accounts, and definitely does not list
transactions for Fidelity Visas, and I have not tested it for any other account
types.

This is an attractive way to download transactions because on the surface it
seems to let us download everything in one shot over an infinite time window.
But there could be limitations that I am not aware of.

Other ways we could fetch transactions from Fidelity:
* Download and parse statement PDFs.
  Last 10 years are available, 1 month at a time.
* Download CSVs from Portfolio > Activity & Orders > History > Download.
  Last 5 years are available, 3 months at a time.
* Use Fidelity's free OFX, Quicken, or Quickbooks support.
  I think I read somewhere that Fidelity hosts an OFX server that goes 3 months
  back. They also have Quicken and Quickbooks support. One part of the problem
  with OFX is I haven't figured out how to get it to work yet, and the other
  part of the problem is that we would need persistent storage to accumulate
  transactions beyond a 3 month window. I'm not sure whether any open source
  clients exist for Quicken and Quickbooks' proprietary OFX-based protocols.
"""


import csv
import shutil
import tempfile
import json
from decimal import Decimal
from bank_wrangler.config import ConfigField
from bank_wrangler import schema
from bank_wrangler.bank.common import (
    FirefoxDownloadDriver,
    fidelity_login,
    add_balance_correcting_transaction,
    assert_issubset,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def name():
    return 'Fidelity'


def empty_config():
    return [
        ConfigField(False, 'Username', None),
        ConfigField(True, 'Password', None),
    ]


def _account_balances(driver):
    """Grab account balances from the Accounts FinApp."""
    driver.switch_to.frame(driver.find_element_by_id('content'))
    driver.switch_to.frame(driver.find_element_by_name('content'))
    driver.switch_to.frame(
        driver.find_element_by_xpath('//iframe[@title="Accounts FinApp"]'))

    accounts_upper = driver.find_elements_by_class_name('account-text')
    accounts_lower = driver.find_elements_by_class_name('account-lower-text')
    accounts = []
    for upper, lower in zip(accounts_upper, accounts_lower):
        lowerleft = lower.text.split('-')[0].strip()
        accounts.append('{} - {}'.format(upper.text, lowerleft))

    amounts = driver.find_elements_by_class_name('amount-text')
    replacements = {ord(ch): '' for ch in ' $,'}
    amounts_text = [amt.text.splitlines()[0].translate(replacements)
                    for amt in amounts]

    return dict(zip(accounts, amounts_text))


def _download(config, tempdir):
    username, password = config

    driver = FirefoxDownloadDriver(tempdir, 'application/csv')

    # Sign in to "Full View" Dashboard.
    driver.get('https://scs.fidelity.com/customeronly/fullview.shtml')
    fidelity_login(driver, username.value, password.value)

    driver.implicitly_wait(30)

    # Grab account balances, which also introduces a helpful delay so
    # we don't mouse over the "My Accounts" menu too soon.
    balances = _account_balances(driver)

    driver.switch_to_default_content()
    driver.switch_to.frame(driver.find_element_by_id('content'))
    driver.switch_to.frame(driver.find_element_by_name('content'))

    # Click My Accounts > Transactions.
    menu_elem = driver.find_element_by_id('leve2Menu2')
    ActionChains(driver).move_to_element(menu_elem).perform()
    wait = WebDriverWait(driver, 5)
    target = (By.LINK_TEXT, 'Transactions')
    wait.until(EC.element_to_be_clickable(target)).click()

    # Set the date range and wait for the new content to load.
    driver.find_element_by_id('dropdown_dateRangeId').click()
    wait = WebDriverWait(driver, 5)
    target = (By.XPATH, '//*[@title="All data available"]')
    wait.until(EC.element_to_be_clickable(target)).click()
    target = "//*[contains(text(), '{}')]".format('Total for all transactions:')
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.XPATH, target)))

    # Submit the form manually instead of pressing download so we don't have to
    # click through a warning dialog.
    driver.find_element_by_id('rep1').submit()

    csv_path = driver.grab_download('ExportData.csv', timeout_seconds=30)
    driver.quit()

    return csv_path, balances


def fetch(config, fileobj):
    with tempfile.TemporaryDirectory() as tempdir:
        csv_path, balances = _download(config, tempdir)
        json.dump(balances, fileobj)
        fileobj.write('\n')
        with open(csv_path, 'r') as csv_file:
            shutil.copyfileobj(csv_file, fileobj)


def transactions(fileobj):
    result = schema.TransactionModel(schema.COLUMNS)
    jsonbalances, _csv_header, *csvlines = iter(fileobj)
    balances_by_account = {
        account: Decimal(balance)
        for account, balance
        in json.loads(jsonbalances).items()
    }
    for _, date, description, _, _, _, signed_amount, _, _, _, account, _ in csv.reader(csvlines):
        month, day, year = map(int, date.split('/'))
        frm, to = 'Universe', account
        amount = Decimal(signed_amount.replace(',', ''))
        if amount < 0:
            frm, to = to, frm
            amount *= -1
        result.ingest_row(
            schema.String(name()),
            schema.String(frm),
            schema.String(to),
            schema.Date(year, month, day),
            schema.String(description),
            schema.Dollars(amount)
        )
    for account, balance in balances_by_account.items():
        add_balance_correcting_transaction(name(), account, balance, result)
    return result


def accounts(fileobj):
    jsonbalances, _csv_header, *csvlines = iter(fileobj)
    all_accounts = json.loads(jsonbalances).keys()
    tabulated_accounts = {account for *_, account, _ in csv.reader(csvlines)}
    assert_issubset(tabulated_accounts, all_accounts)
    return all_accounts
