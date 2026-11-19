"""Strict local test settings shared by pytest and its import-tool subprocess.

The opt-in 27028 mode uses only the sanitized example, never real .env files.
The existing 27017 test workflow remains compatible and guarded.
"""
import os

from dotenv import dotenv_values


def local_test_settings(backend):
    port = os.environ.get('IRASETH_TEST_MONGO_PORT', '27017')
    if port not in ('27017', '27028'):
        raise ValueError('IRASETH_TEST_MONGO_PORT must be 27017 or the disposable test port 27028.')
    path = backend / ('.env.test.example' if port == '27028' else '.env.test')
    if not path.is_file():
        raise ValueError('Missing local test configuration: ' + path.name)
    settings = dict(dotenv_values(path))
    original_uri = 'mongodb://127.0.0.1:27017/?replicaSet=rs0'
    for key, expected in {'APP_ENV': 'testing', 'MONGO_DB_NAME': 'iraseth_test', 'MONGO_URI': original_uri}.items():
        if settings.get(key) != expected:
            raise ValueError('Unsafe test setting ' + key + ': must match approved local test configuration.')
    uri = 'mongodb://127.0.0.1:' + port + '/?replicaSet=rs0'
    settings['MONGO_URI'] = uri
    return settings, uri, int(port)
