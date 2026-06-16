from django.urls import path

from . import views

urlpatterns = [
    path('manage/', views.manage_courses, name='manage_courses'),
    path('programs/', views.manage_programs, name='manage_programs'),
    path('add/', views.add_course, name='add_course'),
    path('edit/<int:pk>/', views.edit_course, name='edit_course'),
    path('programs/add/', views.add_program, name='add_program'),
    path('programs/edit/<int:pk>/', views.edit_program, name='edit_program'),
    path('programs/delete/<int:pk>/', views.delete_program, name='delete_program'),
    path('programs/sync/', views.sync_programs, name='sync_programs'),
    path('import-ug-docx/', views.import_ug_docx, name='import_ug_docx'),
    path('toggle-show-department/', views.toggle_show_department, name='toggle_show_department'),
    path('toggle-compulsory/<int:pk>/', views.toggle_compulsory, name='toggle_compulsory'),
    path('delete/<int:pk>/', views.delete_course, name='delete_course'),
]