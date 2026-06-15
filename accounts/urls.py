from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.registration_view, name='register'),
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
]