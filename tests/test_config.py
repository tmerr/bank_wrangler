import bank_wrangler
from bank_wrangler import config
from nose.tools import assert_equals, assert_raises
import tempfile


def test_put_get():
    config_in = config.Config(
        bank = 'mybank',
        fields = [
            config.ConfigField(False, 'username', 'abc'),
            config.ConfigField(True, 'password', 'xyz'),
        ]
    )
    key = 'somekey'
    vaultpass = 'abcd'
    with tempfile.TemporaryDirectory() as path:
        vault = config.Vault(path)
        vault.write_empty(vaultpass)
        vault.put(key, config_in, vaultpass)
        config_out = vault.get_all(vaultpass)[key]
    assert_equals(config_in, config_out)


def test_put_keys():
    bankname = 'mybank'
    bankconfig = []
    vaultpass = 'abcd'
    with tempfile.TemporaryDirectory() as path:
        vault = config.Vault(path)
        vault.write_empty(vaultpass)
        vault.put(bankname, bankconfig, vaultpass)
        assert_equals(vault.keys(), ['mybank'])


def test_put_delete():
    config_in = config.Config(
        bank = 'mybank',
        fields = [
            config.ConfigField(False, 'username', 'abc'),
            config.ConfigField(True, 'password', 'xyz'),
        ]
    )
    key = 'somekey'
    vaultpass = 'abcd'
    with tempfile.TemporaryDirectory() as path:
        vault = config.Vault(path)
        vault.write_empty(vaultpass)
        vault.put(key, config_in, vaultpass)
        assert_equals(vault.keys(), ['somekey'])
        vault.delete(key, vaultpass)
        assert_equals(vault.keys(), [])
        assert_equals(vault.get_all(vaultpass), {})
