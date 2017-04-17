from bank_wrangler import config
from bank_wrangler.mockio import MockIO
from nose.tools import assert_equals, assert_raises


def test_banks_empty():
    assert_equals(config.list(MockIO()), [])


def test_put_get():
    io = MockIO()
    bankname = 'mybank'
    bankconfig_in = [
        config.ConfigField(False, 'username', 'abc'),
        config.ConfigField(True, 'password', 'xyz'),
    ]
    vaultpass = 'abcd'
    config.put(bankname, bankconfig_in, vaultpass, io)
    bankconfig_out = config.get(bankname, vaultpass, io)
    assert_equals(bankconfig_in, bankconfig_out)


def test_put_list():
    io = MockIO()
    bankname = 'mybank'
    bankconfig = []
    vaultpass = 'abcd'
    config.put(bankname, bankconfig, vaultpass, io)
    assert_equals(config.list(io), ['mybank'])


def test_put_delete():
    io = MockIO()
    bankname = 'mybank'
    bankconfig = [
        config.ConfigField(False, 'username', 'abc'),
        config.ConfigField(True, 'password', 'xyz'),
    ]
    vaultpass = 'abcd'
    config.put(bankname, bankconfig, vaultpass, io)
    assert_equals(config.list(io), ['mybank'])
    config.delete(bankname, vaultpass, io)
    assert_equals(config.list(io), [])
    assert_raises(KeyError, config.get, bankname, vaultpass, io)
