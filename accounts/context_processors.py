from .models import SocialMediaLink


def site_footer_context(request):
    return {
        'social_media_links': SocialMediaLink.objects.filter(is_active=True).order_by(
            'sort_order', 'id'
        ),
    }