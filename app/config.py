"""Environment only configuration. Never put provider credentials in browser code."""
import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv('DATABASE_URL', 'sqlite:///./payguard.db'))
    demo: bool = field(default_factory=lambda: os.getenv('DEMO_MODE', 'true').lower() == 'true')
    secure_cookies: bool = field(default_factory=lambda: os.getenv('SECURE_COOKIES', 'false').lower() == 'true')
    origin: str = field(default_factory=lambda: os.getenv('APP_ORIGIN', 'http://127.0.0.1:8000'))
    paypal_environment: str = field(default_factory=lambda: os.getenv('PAYPAL_ENVIRONMENT', 'sandbox'))
    paypal_client_id: str = field(default_factory=lambda: os.getenv('PAYPAL_CLIENT_ID', ''))
    paypal_secret: str = field(default_factory=lambda: os.getenv('PAYPAL_CLIENT_SECRET', ''))
    paypal_webhook_id: str = field(default_factory=lambda: os.getenv('PAYPAL_WEBHOOK_ID', ''))
    paypal_tenant_id: str = field(default_factory=lambda: os.getenv('PAYPAL_TENANT_ID', ''))
    openai_key: str = field(default_factory=lambda: os.getenv('OPENAI_API_KEY', ''))
    openai_model: str = field(default_factory=lambda: os.getenv('OPENAI_MODEL', ''))

    def validate(self):
        if self.paypal_environment not in ('sandbox', 'live'):
            raise ValueError('PAYPAL_ENVIRONMENT must be sandbox or live')
        if not self.demo and (not self.secure_cookies or not self.origin.startswith('https://')):
            raise ValueError('Production requires HTTPS APP_ORIGIN and SECURE_COOKIES=true')

