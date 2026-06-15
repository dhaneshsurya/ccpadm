from django.urls import path

from . import views

urlpatterns = [
    path('fill-form/', views.fill_admission_form, name='fill_admission_form'),
    path('preview/', views.preview_application, name='preview_application'),
    path('my-application/', views.my_application, name='my_application'),
    path('print/<str:app_no>/', views.print_application, name='print_application'),
    path('download-pdf/', views.download_pdf_page, name='download_pdf_page'),
    path('pdf/<str:app_no>/', views.download_pdf, name='download_pdf'),
    path('api/courses/', views.courses_api, name='courses_api'),
    path('api/save-draft/', views.save_draft_api, name='save_draft_api'),
    path('api/load-draft/', views.load_draft_api, name='load_draft_api'),
    path('api/submit/', views.submit_application, name='submit_application'),
]