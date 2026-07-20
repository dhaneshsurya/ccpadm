"""Shared email backend helpers (SMTP Gmail vs Amazon SES)."""

from __future__ import annotations

import logging
import re

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


def uses_ses_backend() -> bool:
    backend = getattr(settings, 'EMAIL_BACKEND', '') or ''
    return 'django_ses' in backend or getattr(settings, 'USE_SES', False)


def is_email_configured() -> bool:
    if uses_ses_backend():
        return bool((getattr(settings, 'DEFAULT_FROM_EMAIL', '') or '').strip())
    return bool(settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD)


def email_provider_label() -> str:
    return 'Amazon SES' if uses_ses_backend() else 'SMTP'


def get_from_email() -> str:
    """Return a display-friendly From header (Name <address>)."""
    address = (getattr(settings, 'DEFAULT_FROM_EMAIL', '') or '').strip()
    if not address and not uses_ses_backend():
        address = (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip()
    if not address:
        return ''

    # Already formatted: Name <email@domain>
    if '<' in address and '>' in address:
        return address

    name = (getattr(settings, 'EMAIL_FROM_NAME', '') or '').strip()
    if not name:
        name = 'Chaitanya Science & Arts College'
    return f'{name} <{address}>'


def get_public_site_url() -> str:
    url = (getattr(settings, 'PUBLIC_SITE_URL', '') or '').strip().rstrip('/')
    if url:
        return url
    return 'https://online.chaitanyacg.ac.in'


def classify_email_failure(exc: Exception) -> str:
    """Map SMTP / SES exceptions to stable failure codes for user messaging."""
    raw = exc
    if hasattr(exc, 'smtp_error'):
        smtp_error = exc.smtp_error
        if isinstance(smtp_error, bytes):
            raw = smtp_error.decode('utf-8', errors='replace')
        else:
            raw = str(smtp_error)
    if hasattr(exc, 'response'):
        response = getattr(exc, 'response', None)
        if isinstance(response, dict):
            raw = f'{raw} {response.get("Error", {}).get("Message", "")}'
    text = f'{exc} {raw}'.lower()

    if 'daily user sending limit' in text or 'sending limit exceeded' in text:
        return 'daily_limit'
    if 'message blocked' in text or 'mail delivery subsystem' in text or '550-5.7.1' in text:
        return 'blocked'
    if 'email address is not verified' in text or 'messagerejected' in text:
        return 'ses_not_verified'
    if 'accessdenied' in text or 'not authorized' in text:
        return 'ses_permission'
    if 'username and password not accepted' in text or 'authentication failed' in text:
        return 'auth_error'
    if 'connection refused' in text or 'timed out' in text or 'network is unreachable' in text:
        return 'connection_error'
    return 'smtp_error'


def get_ses_send_quota():
    """Return SES quota dict or None if unavailable."""
    if not uses_ses_backend():
        return None
    try:
        import boto3
    except ImportError:
        return None

    region = getattr(settings, 'AWS_SES_REGION_NAME', 'ap-south-1')
    client = boto3.client('ses', region_name=region)
    return client.get_send_quota()


def send_transactional_email(
    *,
    subject: str,
    text_body: str,
    to_email: str,
    html_body: str = '',
) -> tuple[bool, str]:
    """
    Send a transactional email with proper From header.
    Returns (success, reason_code).
    """
    to_email = (to_email or '').strip()
    if not to_email:
        return False, 'missing_email'
    if not is_email_configured():
        return False, 'not_configured'

    from_email = get_from_email()
    if not from_email:
        return False, 'not_configured'

    # Guard: Gmail SMTP requires From to match authenticated account.
    if not uses_ses_backend():
        host_user = (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip().lower()
        match = re.search(r'<([^>]+)>', from_email)
        from_addr = (match.group(1) if match else from_email).strip().lower()
        if host_user and from_addr and from_addr != host_user:
            logger.warning(
                'DEFAULT_FROM_EMAIL (%s) differs from EMAIL_HOST_USER (%s); '
                'Gmail may rewrite or block the message. Using EMAIL_HOST_USER as From.',
                from_addr,
                host_user,
            )
            name = (getattr(settings, 'EMAIL_FROM_NAME', '') or 'Chaitanya Science & Arts College').strip()
            from_email = f'{name} <{host_user}>'

    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_email,
            to=[to_email],
        )
        if html_body:
            message.attach_alternative(html_body, 'text/html')
        message.send(fail_silently=False)
        return True, 'sent'
    except Exception as exc:
        reason = classify_email_failure(exc)
        logger.error('Failed to send email to %s (%s): %s', to_email, reason, exc)
        return False, reason
