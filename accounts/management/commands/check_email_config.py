from django.conf import settings
from django.core.management.base import BaseCommand

from accounts.utils import is_email_configured


class Command(BaseCommand):
    help = 'Verify SMTP email settings used for OTP and registration emails.'

    def handle(self, *args, **options):
        env_path = settings.BASE_DIR / '.env'
        self.stdout.write(f'.env path: {env_path} (exists: {env_path.exists()})')
        self.stdout.write(f'EMAIL_HOST: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}')
        self.stdout.write(f'EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}')
        self.stdout.write(f'EMAIL_HOST_USER: {settings.EMAIL_HOST_USER or "(not set)"}')
        self.stdout.write(
            'EMAIL_HOST_PASSWORD: '
            + ('set (' + str(len(settings.EMAIL_HOST_PASSWORD)) + ' chars)' if settings.EMAIL_HOST_PASSWORD else '(not set)')
        )
        self.stdout.write(f'DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL or "(not set)"}')

        if not is_email_configured():
            self.stderr.write(self.style.ERROR(
                'Email is NOT configured. Set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env'
            ))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS('Email configuration looks OK.'))