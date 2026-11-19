"""Create missing local environment files exclusively; preserve existing files."""
import argparse
import os
from pathlib import Path
import secrets
import sys

from dotenv import dotenv_values
from setup_local_catalog import validate_target, DEFAULT_DATABASE, DEFAULT_URI

ROOT = Path(__file__).resolve().parents[2]


def configure_files(root, database, uri, check=False):
    validate_target(database, uri)
    for key, expected in {'APP_ENV': 'development', 'DEPLOYMENT_ENVIRONMENT': '',
                          'MONGO_DB_NAME': database, 'MONGO_URI': uri}.items():
        if key in os.environ and os.environ[key] != expected:
            raise ValueError('Shell variable ' + key + ' overrides the selected local environment. It was preserved; use a clean terminal or explicitly configure it yourself.')
    backend = root / 'backend/.env'
    if database == 'iraseth_dev' and not backend.exists():
        raise ValueError('Reusing iraseth_dev requires its existing backend/.env. It is report-only; use the default iraseth for a new environment.')
    if backend.exists():
        settings = dotenv_values(backend)
        if (settings.get('APP_ENV') != 'development' or settings.get('DEPLOYMENT_ENVIRONMENT', '')
                or settings.get('MONGO_DB_NAME') != database or settings.get('MONGO_URI') != uri):
            raise ValueError('backend/.env targets another environment. It was preserved. Use a separate clone for this new local database, or explicitly configure it yourself.')
    plans = {
        backend: ('backend/.env.example', {'APP_ENV': 'development', 'DEPLOYMENT_ENVIRONMENT': '',
                  'MONGO_DB_NAME': database, 'MONGO_URI': uri, 'BATCH_MODE': 'true',
                  'JWT_SECRET': secrets.token_hex(32),
                  'CORS_ORIGINS': 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000'}),
        root / 'frontend/.env': ('frontend/.env.example', {}),
        root / 'storefront-next/.env.local': ('storefront-next/.env.example', {}),
    }
    for path, (template, replacements) in plans.items():
        if path.parent.name in ('frontend', 'storefront-next'):
            # Creating .env.local would silently shadow an existing Next .env
            # or .env.development. Preserve effective settings, not just bytes.
            existing = [path.parent / name for name in ('.env', '.env.local', '.env.development', '.env.development.local')
                        if (path.parent / name).exists()]
            if existing:
                for old in existing:
                    print('Preserved ' + str(old.relative_to(root)))
                continue
        if path.exists():
            print('Preserved ' + str(path.relative_to(root)))
            continue
        text = (root / template).read_text(encoding='utf-8')
        for key, value in replacements.items():
            text = '\n'.join(key + '=' + value if line.startswith(key + '=') else line for line in text.split('\n'))
        if check:
            print('Missing ' + str(path.relative_to(root)) + ' (run setup without -Status to create)')
        else:
            with path.open('x', encoding='utf-8', newline='\n') as stream:
                stream.write(text)
            print('Created ' + str(path.relative_to(root)))
    print('Expected Flask origin: http://127.0.0.1:5000. Existing frontend/Next overrides and shell variables are preserved; check them if connectivity differs.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default=DEFAULT_DATABASE)
    parser.add_argument('--uri', default=DEFAULT_URI)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        configure_files(ROOT, args.database, args.uri, args.check)
    except (ValueError, OSError) as exc:
        print('Environment setup stopped: ' + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
