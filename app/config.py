"""Environment only configuration. Never put provider credentials in browser code."""
import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit


@dataclass
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv('DATABASE_URL', 'sqlite:///./payguard.db'))
    demo: bool = field(default_factory=lambda: os.getenv('DEMO_MODE', 'true').lower() == 'true')
    secure_cookies: bool = field(default_factory=lambda: os.getenv('SECURE_COOKIES', 'false').lower() == 'true')
    origin: str = field(default_factory=lambda: os.getenv('APP_ORIGIN', 'http://127.0.0.1:3000'))
    paypal_environment: str = field(default_factory=lambda: os.getenv('PAYPAL_ENVIRONMENT', 'sandbox'))
    paypal_client_id: str = field(default_factory=lambda: os.getenv('PAYPAL_CLIENT_ID', ''))
    paypal_secret: str = field(default_factory=lambda: os.getenv('PAYPAL_CLIENT_SECRET', ''))
    paypal_webhook_id: str = field(default_factory=lambda: os.getenv('PAYPAL_WEBHOOK_ID', ''))
    paypal_tenant_id: str = field(default_factory=lambda: os.getenv('PAYPAL_TENANT_ID', ''))
    openai_key: str = field(default_factory=lambda: os.getenv('OPENAI_API_KEY', ''))
    openai_model: str = field(default_factory=lambda: os.getenv('OPENAI_MODEL', ''))
    ai_provider: str = field(default_factory=lambda: os.getenv('AI_PROVIDER', 'auto').lower())
    groq_key: str = field(default_factory=lambda: os.getenv('GROQ_API_KEY', ''))
    groq_model: str = field(default_factory=lambda: os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b'))
    groq_schema_recovery: bool = field(default_factory=lambda: os.getenv('GROQ_SCHEMA_RECOVERY', 'false').lower() == 'true')

    @property
    def drafting_provider(self):
        if self.ai_provider != 'auto':
            return self.ai_provider
        return 'groq' if self.groq_key else 'openai' if self.openai_key else 'template'

    def ai_status(self):
        provider = self.drafting_provider
        key = self.groq_key if provider == 'groq' else self.openai_key if provider == 'openai' else ''
        model = self.groq_model if provider == 'groq' else self.openai_model if provider == 'openai' else ''
        configured = bool(key and model)
        if provider == 'template':
            message = ('Groq key detected, but AI_PROVIDER=template disables AI. Set AI_PROVIDER=groq and restart the backend.' if self.groq_key else 'Offline template mode. Set AI_PROVIDER=groq and GROQ_API_KEY in the backend .env, then restart both servers.')
        elif not configured:
            message = f'{provider.upper()} is selected, but its backend API key or model is missing. Update .env and restart both servers.'
        else:
            message = f'{provider.upper()} is configured. Test the connection, then open a case to generate an AI response. Human approval is always required.'
        return {'ai_provider': provider, 'ai_model': model, 'ai_configured': configured, 'groq_key_present': bool(self.groq_key), 'ai_message': message}

    def __post_init__(self):
        # Managed providers commonly supply driver-neutral PostgreSQL URLs.
        for prefix in ('postgres://', 'postgresql://'):
            if self.database_url.startswith(prefix):
                self.database_url = 'postgresql+psycopg://' + self.database_url[len(prefix):]
                break

    def validate(self):
        if self.ai_provider not in {'auto', 'template', 'groq', 'openai'}:
            raise ValueError('AI_PROVIDER must be auto, template, groq or openai')
        parsed = urlsplit(self.origin)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
            raise ValueError('APP_ORIGIN must be the exact frontend HTTP(S) origin, without credentials, path, query or fragment')
        self.origin = self.origin.rstrip('/')
        if self.paypal_environment not in ('sandbox', 'live'):
            raise ValueError('PAYPAL_ENVIRONMENT must be sandbox or live')
        if not self.demo and (not self.secure_cookies or not self.origin.startswith('https://')):
            raise ValueError('Production requires HTTPS APP_ORIGIN and SECURE_COOKIES=true')
