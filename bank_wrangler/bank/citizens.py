import csv
import shutil
import tempfile
from decimal import Decimal
from selenium.webdriver.common.keys import Keys
from bank_wrangler.config import ConfigField
from bank_wrangler import schema
from bank_wrangler.bank.common import FirefoxDownloadDriver


NUM_SECURITY_QUESTIONS = 3


def name():
    return 'Citizens Bank'


def empty_config():
    return [
        ConfigField(False, 'Username', None),
        ConfigField(True, 'Password', None),
        ConfigField(False, 'Part of security question 1', None),
        ConfigField(False, 'Answer 1', None),
        ConfigField(False, 'Part of security question 2', None),
        ConfigField(False, 'Answer 2', None),
        ConfigField(False, 'Part of security question 3', None),
        ConfigField(False, 'Answer 3', None),
    ]


def _answer_security_question(question, cfg_security):
    for i in range(0, 2 * NUM_SECURITY_QUESTIONS, 2):
        question_part = cfg_security[i].value
        answer = cfg_security[i+1].value
        if question_part in question:
            return answer
    raise Exception(f'unrecognized security question "{question}"')


def _download(config, tempdir):
    cfg_user, cfg_pass, *cfg_security = config

    driver = FirefoxDownloadDriver(tempdir, 'application/binary')
    driver.get('https://www.citizensbankonline.com/efs/servlet/efs/login.jsp')

    # Sign in
    user = driver.find_element_by_id('UserID')
    user.clear()
    user.send_keys(cfg_user.value)
    password = driver.find_element_by_id('currentpassword')
    password.clear()
    password.send_keys(cfg_pass.value)
    password.send_keys(Keys.RETURN)

    # Set an implicit wait (which defaults to 0) to save us from
    # accessing elements before they are ready.
    driver.implicitly_wait(15)

    # Switch into the AJAX-created frame that contains the security question
    # then answer it.
    driver.switch_to.frame(driver.find_element_by_name('mainFrame'))
    question_elem = driver.find_element_by_xpath("//label[@for='Response']")
    answer_elem = driver.find_element_by_id('Response')
    answer = _answer_security_question(question_elem.text, cfg_security)
    answer_elem.send_keys(answer)
    answer_elem.send_keys(Keys.RETURN)

    # Click "Download transactions", set options, and download.
    download_elem = driver.find_element_by_class_name('account-transactions-download')
    download_elem.click()
    driver.find_element_by_xpath('.//option[normalize-space(.) = "All Dates"]').click()
    driver.find_element_by_xpath('.//option[normalize-space(.) = "Comma Delimited"]').click()
    # Selenium sometimes misclicks the download button, so just call its onclick javascript.
    driver.execute_script('setFilterValues()')
    csv_path = driver.grab_download('EXPORT.CSV', timeout_seconds=30)

    driver.quit()
    return csv_path


def fetch(config, fileobj):
    with tempfile.TemporaryDirectory() as tempdir:
        csv_path = _download(config, tempdir)
        with open(csv_path, 'r') as csv_file:
            shutil.copyfileobj(csv_file, fileobj)


def _parse_dollars(string):
    return Decimal(string.replace(',', '').replace('$', ''))


def transactions(fileobj):
    result = schema.TransactionModel(schema.COLUMNS)
    lines = list(csv.reader(fileobj))[1:]
    for _, date, account_type, description, amount_str, _, credit_str, debit_str in lines:
        amount = _parse_dollars(amount_str)
        frm, to = 'Universe', f'Citizens {account_type}'

        if amount < 0:
            frm, to = to, frm
            amount *= -1
            assert amount == _parse_dollars(debit_str)
        else:
            assert amount == _parse_dollars(credit_str)

        # change MM/DD/YY to YYYY/MM/DD.
        month, day, year = map(int, date.split('/'))
        year = 2000 + year
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
    return {'Citizens {}'.format(account_type) for _, _, account_type, *_ in lines}
