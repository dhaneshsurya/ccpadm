from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('students/', views.manage_students, name='manage_students'),
    path('students/edit/<int:pk>/', views.edit_student, name='edit_student'),
    path('students/delete/<int:pk>/', views.delete_student, name='delete_student'),
    path('students/reset-password/<int:pk>/', views.reset_student_password, name='reset_student_password'),
    path('students/toggle-verified/<int:pk>/', views.toggle_student_verified, name='toggle_student_verified'),
    path('students/bulk-action/', views.bulk_student_action, name='bulk_student_action'),
    path('students/export/', views.export_students_csv, name='export_students_csv'),
    path('merit-list/', views.merit_list, name='merit_list'),
    path('merit-list/export/', views.export_merit_list_csv, name='export_merit_list_csv'),
    path('merit-list/export/excel/', views.export_merit_list_excel, name='export_merit_list_excel'),
    path('students/print/<str:app_no>/', views.admin_print_application, name='admin_print_application'),
    path('students/pdf/<str:app_no>/', views.admin_download_pdf, name='admin_download_pdf'),
    path('admission/<int:pk>/status/', views.update_admission_status, name='update_admission_status'),
    path('admissions/bulk-status/', views.bulk_update_admission_status, name='bulk_update_admission_status'),
]