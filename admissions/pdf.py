import os
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.template.loader import render_to_string
from xhtml2pdf import pisa

from .services import get_application_print_view_context, write_image_for_pdf


def _resolve_uri(uri):
    """Convert file:// and relative URIs to absolute filesystem paths for xhtml2pdf."""
    if not uri:
        return uri
    if uri.startswith('file:'):
        parsed = urlparse(uri)
        path = unquote(parsed.path)
        if os.name == 'nt' and path.startswith('/') and len(path) > 2 and path[2] == ':':
            path = path[1:]
        return path
    if os.path.isabs(uri):
        return uri
    static_root = Path(settings.BASE_DIR) / 'static'
    candidate = static_root / uri.lstrip('/')
    if candidate.exists():
        return str(candidate.resolve())
    return uri


def link_callback(uri, rel):
    return _resolve_uri(uri)


def render_admission_pdf(admission, request=None):
    context = get_application_print_view_context(admission, preview_mode=False)
    context['is_pdf'] = True

    logo_path = (settings.BASE_DIR / 'static' / 'images' / 'logo.png').resolve()
    naac_path = (settings.BASE_DIR / 'static' / 'images' / 'NAAC.png').resolve()
    context['logo_url'] = str(logo_path)
    context['naac_url'] = str(naac_path)

    app_no = admission.application_no or 'application'
    if context.get('photo_src'):
        context['photo_src'] = write_image_for_pdf(admission.photo_base64, f'{app_no}_photo_')
    if context.get('sign_src'):
        context['sign_src'] = write_image_for_pdf(admission.signature_base64, f'{app_no}_sign_')

    html = render_to_string('admissions/print_full.html', context)
    result = BytesIO()
    pdf = pisa.CreatePDF(
        html,
        dest=result,
        encoding='utf-8',
        link_callback=link_callback,
    )
    if pdf.err:
        raise RuntimeError('PDF generation failed')
    result.seek(0)
    return result