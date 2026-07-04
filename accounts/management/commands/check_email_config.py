from django.conf import settings
from django.core.mail import get_connection
from django.core.management.base import BaseCommand

from accounts.utils import is_email_configured


class Command(BaseCommand):
    help = 'Verify SMTP email settings used for OTP and registration emails.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-smtp',
            action='store_true',
            help='Open an SMTP connection to verify host, port, and credentials.',
        )

    def handle(self, *args, **options):
        env_path = settings.BASE_DIR / '.env'
        self.stdout.write(f'.env path: {env_path} (exists: {env_path.exists()})')
        self.stdout.write(f'DEBUG: {settings.DEBUG}')
        self.stdout.write(f'EMAIL_HOST: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}')
        self.stdout.write(f'EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}')
        self.stdout.write(f'EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}')
        self.stdout.write(f'EMAIL_HOST_USER: {settings.EMAIL_HOST_USER or "(not set)"}')
        self.stdout.write(
            'EMAIL_HOST_PASSWORD: '
            + (
                'set (' + str(len(settings.EMAIL_HOST_PASSWORD)) + ' chars)'
                if settings.EMAIL_HOST_PASSWORD
                else '(not set)'
            )
        )
        self.stdout.write(f'DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL or "(not set)"}')

        if not is_email_configured():
            self.stderr.write(self.style.ERROR(
                'Email is NOT configured. Create /home/ubuntu/django_ccp/.env on the server '
                '(copy from .env.example) and set EMAIL_HOST_USER + EMAIL_HOST_PASSWORD '
                '(Gmail App Password, not your normal login password).'
            ))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS('Email variables are set.'))

        if not options['test_smtp']:
            self.stdout.write('Run with --test-smtp to verify SMTP login.')
            return

        self.stdout.write('Testing SMTP connection...')
        try:
            connection = get_connection(
                backend=settings.EMAIL_BACKEND,
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                use_tls=settings.EMAIL_USE_TLS,
                use_ssl=settings.EMAIL_USE_SSL,
                timeout=settings.EMAIL_TIMEOUT,
            )
            connection.open()
            connection.close()
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'SMTP connection failed: {exc}'))
            self.stderr.write(
                'Check Gmail App Password, 2-Step Verification, and whether port 587 is open. '
                'If blocked, try EMAIL_PORT=465, EMAIL_USE_SSL=True, EMAIL_USE_TLS=False in .env.'
            )
            raise SystemExit(1) from exc

        self.stdout.write(self.style.SUCCESS('SMTP connection OK.'))