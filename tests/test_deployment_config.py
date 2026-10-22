import pytest
from app.config import Settings


@pytest.mark.parametrize('scheme', ['postgres', 'postgresql'])
def test_hosted_database_url_uses_installed_driver(scheme):
    settings = Settings(database_url=f'{scheme}://user:password@db:5432/payguard?sslmode=require')
    assert settings.database_url == 'postgresql+psycopg://user:password@db:5432/payguard?sslmode=require'


def test_frontend_origin_is_exact_and_normalized():
    settings = Settings(origin='https://payguard.vercel.app/')
    settings.validate()
    assert settings.origin == 'https://payguard.vercel.app'
    for origin in ['*', 'https://app.test/path', 'https://user:secret@app.test', 'https://app.test?token=value']:
        with pytest.raises(ValueError): Settings(origin=origin).validate()
