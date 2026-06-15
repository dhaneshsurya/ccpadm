from .models import SocialMediaLink


def site_footer_context(request):
    return {
        'social_media_links': SocialMediaLink.objects.filter(is_active=True).order_by(
            'sort_order', 'id'
        ),
        'is_student_logged_in': bool(request.session.get('is_logged_in')),
        'is_admin_logged_in': bool(request.session.get('admin_user')),
        'student_name': request.session.get('student_name', ''),
    }