import os
import time
import csv
import shutil
import tempfile
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from bank_wrangler.config import ConfigField
from bank_wrangler import schema


NUM_SECURITY_QUESTIONS = 3


def name():
    return 'Citizens Bank'


def filename():
    return 'citizens.csv'


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

    # Set preferences to skip the prompt when downloading the csv.
    SPECIFY_FOLDER = 2
    profile = webdriver.FirefoxProfile()
    profile.set_preference('browser.helperApps.neverAsk.saveToDisk', 'application/binary')
    profile.set_preference('browser.download.folderList', SPECIFY_FOLDER)
    profile.set_preference('browser.download.dir', tempdir)
    driver = webdriver.Firefox(profile)

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
    driver.execute_script('setFilterValues()') # selenium is misclicking the button, call JS directly.

    # Wait on file to appear and file.part to disappear.
    csv_path = os.path.join(tempdir, 'EXPORT.CSV')
    part_path = csv_path + '.part'
    for timeout in range(30, 0, -1):
        time.sleep(1)
        if os.path.isfile(csv_path) and not os.path.isfile(part_path):
            break
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
    for _, date, account_type, description, _, _, credit, debit in lines:
        is_debit = len(debit) > 0 and len(credit) == 0
        is_credit = len(credit) > 0 and len(debit) == 0
        a = 'Citizens {}'.format(account_type)
        b = 'Universe'

        if is_debit:
            assert not is_credit
            from_to = [a, b]
            amount = debit
        else:
            assert is_credit
            from_to = [b, a]
            amount = credit

        month, day, year = map(int, date.split('/'))
        result.ingest_row(
            schema.String(name()),
            schema.String(from_to[0]),
            schema.String(from_to[1]),
            schema.Date(year, month, day),
            schema.String(description),
            schema.Dollars(amount)
        )
    return result


def accounts(fileobj):
    lines = list(csv.reader(fileobj))[1:]
    return { 'Citizens {}'.format(account_type) for _, _, account_type, *_ in lines }
