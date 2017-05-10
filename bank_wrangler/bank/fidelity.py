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
from decimal import Decimal
from bank_wrangler.config import ConfigField
from bank_wrangler import schema
from bank_wrangler.bank.common import FirefoxDownloadDriver, fidelity_login
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def name():
    return 'Fidelity'


def filename():
    return 'fidelity.csv'


def empty_config():
    return [
        ConfigField(False, 'Username', None),
        ConfigField(True, 'Password', None),
    ]


def _download(config, tempdir):
    username, password = config

    driver = FirefoxDownloadDriver(tempdir, 'application/csv')

    # Sign in to "Full View" Dashboard.
    driver.get('https://scs.fidelity.com/customeronly/fullview.shtml')
    fidelity_login(driver, username.value, password.value)

    # Navigate through the jungle of frames.
    driver.implicitly_wait(30)
    driver.switch_to.frame(driver.find_element_by_id('content'))
    driver.switch_to.frame(driver.find_element_by_name('content'))

    # Wait until this arbitrary iframe loads before clicking through menus.
    # This adds a conservative delay that fixes an issue where sometimes
    # the upcoming mouse move onto the menu doesn't do anything.
    driver.switch_to.frame(
        driver.find_element_by_xpath('//iframe[@title="Net Worth Performance FinApp"]'))
    driver.find_element_by_id('todays-networth')

    driver.switch_to_default_content()
    driver.switch_to.frame(driver.find_element_by_id('content'))
    driver.switch_to.frame(driver.find_element_by_name('content'))

    # Click My Account > Transactions.
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

    return csv_path


def fetch(config, fileobj):
    with tempfile.TemporaryDirectory() as tempdir:
        csv_path = _download(config, tempdir)
        with open(csv_path, 'r') as csv_file:
            shutil.copyfileobj(csv_file, fileobj)


def transactions(fileobj):
    result = schema.TransactionModel(schema.COLUMNS)
    lines = list(csv.reader(fileobj))[1:]
    for _, date, description, _, _, _, signed_amount, _, _, _, account, _ in lines:
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
    return result


def accounts(fileobj):
    lines = list(csv.reader(fileobj))[1:]
    return {account for *_, account, _ in lines}
