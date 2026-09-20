from django.urls import path

from . import views

app_name = "agenda"

urlpatterns = [
    path("", views.home, name="home"),
    path("cadastro/", views.cadastro, name="cadastro"),
    path("agendar/", views.agendar, name="agendar"),
    path("agendamentos/<int:pk>/cancelar/", views.cancelar, name="cancelar"),
]