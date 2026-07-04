from django.conf import settings
from django.core.mail import get_connection, send_mail
from django.core.management.base import BaseCommand

from accounts.email_config import (
    email_provider_label,
    get_ses_send_quota,
    is_email_configured,
    uses_ses_backend,
)


class Command(BaseCommand):
    help = 'Verify email settings used for OTP and registration emails (SMTP or Amazon SES).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-smtp',
            action='store_true',
            help='Open an SMTP connection (SMTP mode only).',
        )
        parser.add_argument(
            '--test-send',
            action='store_true',
            help='Send one test message using the configured backend.',
        )
        parser.add_argument(
            '--to',
            default='',
            help='Recipient for --test-send (defaults to DEFAULT_FROM_EMAIL).',
        )

    def handle(self, *args, **options):
        env_path = settings.BASE_DIR / '.env'
        provider = email_provider_label()

        self.stdout.write(f'.env path: {env_path} (exists: {env_path.exists()})')
        self.stdout.write(f'Provider: {provider}')
        self.stdout.write(f'DEBUG: {settings.DEBUG}')
        self.stdout.write(f'EMAIL_BACKEND: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL or "(not set)"}')

        if uses_ses_backend():
            self._print_ses_settings()
        else:
            self._print_smtp_settings()

        if not is_email_configured():
            self.stderr.write(self.style.ERROR(self._not_configured_message()))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS('Email configuration variables look OK.'))

        if uses_ses_backend():
            self._print_ses_quota()

        if options['test_smtp']:
            if uses_ses_backend():
                self.stderr.write(self.style.WARNING('--test-smtp is for SMTP mode only. Use --test-send with SES.'))
            else:
                self._test_smtp_connection()

        if options['test_send']:
            recipient = (options['to'] or settings.DEFAULT_FROM_EMAIL or '').strip()
            if not recipient:
                self.stderr.write(self.style.ERROR('--test-send needs --to or DEFAULT_FROM_EMAIL.'))
                raise SystemExit(1)
            self._test_send(recipient)

        if not options['test_smtp'] and not options['test_send']:
            hint = '--test-send'
            if not uses_ses_backend():
                hint = '--test-smtp or --test-send'
            self.stdout.write(f'Run with {hint} to verify delivery.')

    def _print_smtp_settings(self):
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

    def _print_ses_settings(self):
        self.stdout.write(f'USE_SES: {getattr(settings, "USE_SES", False)}')
        self.stdout.write(f'AWS_SES_REGION_NAME: {getattr(settings, "AWS_SES_REGION_NAME", "(not set)")}')
        has_key = bool(getattr(settings, 'AWS_ACCESS_KEY_ID', None))
        self.stdout.write(
            'AWS credentials: '
            + ('access key in .env' if has_key else 'using EC2 IAM role / default AWS credential chain')
        )

    def _print_ses_quota(self):
        try:
            quota = get_ses_send_quota()
        except Exception as exc:
            self.stderr.write(self.style.WARNING(f'Could not read SES quota: {exc}'))
            self.stderr.write(
                'Attach an IAM role with ses:SendEmail and ses:GetSendQuota to the EC2 instance, '
                'or set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY in .env.'
            )
            return

        if not quota:
            return

        self.stdout.write(f'SES Max24HourSend: {quota.get("Max24HourSend")}')
        self.stdout.write(f'SES SentLast24Hours: {quota.get("SentLast24Hours")}')
        self.stdout.write(f'SES MaxSendRate: {quota.get("MaxSendRate")} emails/sec')
        if quota.get('Max24HourSend') == 200.0:
            self.stdout.write(self.style.WARNING(
                'SES appears to be in SANDBOX mode (200/day). Request production access in AWS SES console.'
            ))

    def _test_smtp_connection(self):
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
            raise SystemExit(1) from exc
        self.stdout.write(self.style.SUCCESS('SMTP connection OK.'))

    def _test_send(self, recipient):
        self.stdout.write(f'Sending test email to {recipient}...')
        try:
            send_mail(
                'CCP Email Test',
                'If you received this, email delivery is working.',
                settings.DEFAULT_FROM_EMAIL,
                [recipient],
                fail_silently=False,
            )
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'Test send failed: {exc}'))
            if uses_ses_backend():
                self.stderr.write(
                    'Verify the FROM address/domain in SES, and recipient if account is still in sandbox.'
                )
            raise SystemExit(1) from exc
        self.stdout.write(self.style.SUCCESS('Test email sent successfully.'))

    def _not_configured_message(self):
        if uses_ses_backend():
            return (
                'SES is enabled but DEFAULT_FROM_EMAIL is not set. '
                'Verify an email or domain in AWS SES, then set DEFAULT_FROM_EMAIL in .env.'
            )
        return (
            'Email is NOT configured. Set EMAIL_HOST_USER + EMAIL_HOST_PASSWORD in .env '
            'or enable USE_SES=True with DEFAULT_FROM_EMAIL.'
        )