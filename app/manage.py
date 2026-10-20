"""Explicit schema initialization; production startup never silently migrates tables."""
import argparse
from sqlalchemy import select
from .config import Settings
from .models import Base, Tenant, database


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['init-db', 'tenants'])
    args = parser.parse_args()
    engine, sessions = database(Settings().database_url)
    if args.command == 'init-db':
        Base.metadata.create_all(engine)
        print('Schema initialized. Use versioned migrations for future schema changes.')
    else:
        with sessions() as db:
            for tenant in db.scalars(select(Tenant)):
                print(tenant.id, tenant.name)


if __name__ == '__main__':
    main()

