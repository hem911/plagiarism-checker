from django.urls import path

from . import views

urlpatterns = [
    path('health/', views.health, name='health'),
    path('check-plagiarism/', views.check_plagiarism, name='check-plagiarism'),
]
