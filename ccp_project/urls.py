from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('ckeditor5/', include('django_ckeditor_5.urls')),
    path('django-admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('admission/', include('admissions.urls')),
    path('admin/', include('admin_panel.urls')),
    path('courses/', include('courses.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])