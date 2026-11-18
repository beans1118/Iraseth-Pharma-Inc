"""Pure validation tests; never connect to MongoDB or create users."""
from pathlib import Path
import importlib.util
from types import SimpleNamespace
import pytest

script = Path(__file__).resolve().parents[1] / 'tools' / 'create_local_test_accounts.py'
spec = importlib.util.spec_from_file_location('local_accounts_tool', script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def config(host='127.0.0.1', name='iraseth_dev', env='development'):
    return SimpleNamespace(MONGO_URI=f'mongodb://{host}:27017/?replicaSet=rs0', MONGO_DB_NAME=name, APP_ENV=env)


def test_local_development_allowed():
    module.ensure_local_target(config())


@pytest.mark.parametrize('cfg', [config(host='mongodb.example.org'),config(name='iraseth_pharma'),config(env='production')])
def test_unsafe_target_blocked(cfg):
    with pytest.raises(ValueError):
        module.ensure_local_target(cfg)


def test_three_distinct_roles_and_passwords():
    answers = iter(['Tester One', 'one@example.test','Tester Two','two@example.test','Tester Three','three@example.test'])
    passwords = iter(['UniquePass1111','UniquePass1111','UniquePass2222','UniquePass2222','UniquePass3333','UniquePass3333'])
    rows = module.collect_accounts(lambda prompt: next(answers), lambda prompt: next(passwords))
    assert [row['role'] for row in rows] == ['superadmin','admin','subadmin']
    assert len({row['email'] for row in rows}) == 3


def test_duplicate_emails_rejected():
    answers = iter(['Tester One','same@example.test','Tester Two','same@example.test'])
    passwords = iter(['UniquePass1111']*4)
    with pytest.raises(ValueError):
        module.collect_accounts(lambda prompt: next(answers),lambda prompt: next(passwords))
