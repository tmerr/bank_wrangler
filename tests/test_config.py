import bank_wrangler
from bank_wrangler import config
from bank_wrangler.mockio import MockIO
from nose.tools import assert_equals, assert_raises


def test_put_get():
    io = MockIO()
    config_in = config.Config(
        bank = 'mybank',
        fields = [
            config.ConfigField(False, 'username', 'abc'),
            config.ConfigField(True, 'password', 'xyz'),
        ]
    )
    key = 'somekey'
    vaultpass = 'abcd'
    config.init(vaultpass, io)
    config.put(key, config_in, vaultpass, io)
    config_out = config.get(key, vaultpass, io)
    assert_equals(config_in, config_out)


def test_put_keys():
    io = MockIO()
    bankname = 'mybank'
    bankconfig = []
    vaultpass = 'abcd'
    config.init(vaultpass, io)
    config.put(bankname, bankconfig, vaultpass, io)
    assert_equals(config.keys(io), ['mybank'])


def test_put_delete():
    io = MockIO()
    config_in = config.Config(
        bank = 'mybank',
        fields = [
            config.ConfigField(False, 'username', 'abc'),
            config.ConfigField(True, 'password', 'xyz'),
        ]
    )
    key = 'somekey'
    vaultpass = 'abcd'
    config.init(vaultpass, io)
    config.put(key, config_in, vaultpass, io)
    assert_equals(config.keys(io), ['somekey'])
    config.delete(key, vaultpass, io)
    assert_equals(config.keys(io), [])
    assert_raises(KeyError, config.get, key, vaultpass, io)
