# Em leitores/urls.py

from django.urls import path
from . import views

# Define um 'namespace' para este app.
app_name = 'leitores' 

urlpatterns = [
    # (READ) /leitores/
    path('', views.consultar_leitores_view, name='leitor_list'),
    
    # (CREATE) /leitores/novo/
    path('novo/', views.cadastrar_leitor_view, name='cadastrar_leitor'),
    
    # (UPDATE) /leitores/atualizar/5/
    path('atualizar/<int:pk>/', views.atualizar_leitor_view, name='atualizar_leitor'),
    
    # (DELETE) /leitores/excluir/5/
    path('excluir/<int:pk>/', views.excluir_leitor_view, name='excluir_leitor'),
]