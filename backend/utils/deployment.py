"""Pure staging-target checks. No connections, credentials or database writes."""
from urllib.parse import urlsplit


def validate_staging_target(app_env, database_name, uri):
    if app_env != 'production' or database_name != 'iraseth_staging':
        raise ValueError('Staging requires APP_ENV=production and MONGO_DB_NAME=iraseth_staging.')
    try:
        parsed = urlsplit(uri)
        atlas = parsed.scheme == 'mongodb+srv' and (parsed.hostname or '').endswith('.mongodb.net')
        if not atlas or parsed.port is not None:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError('Staging requires the Atlas mongodb+srv URI; local or non-Atlas targets are refused.') from None
