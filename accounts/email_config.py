"""Shared email backend helpers (SMTP Gmail vs Amazon SES)."""

from django.conf import settings


def uses_ses_backend() -> bool:
    backend = getattr(settings, 'EMAIL_BACKEND', '') or ''
    return 'django_ses' in backend or getattr(settings, 'USE_SES', False)


def is_email_configured() -> bool:
    if uses_ses_backend():
        return bool((getattr(settings, 'DEFAULT_FROM_EMAIL', '') or '').strip())
    return bool(settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD)


def email_provider_label() -> str:
    return 'Amazon SES' if uses_ses_backend() else 'SMTP'


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