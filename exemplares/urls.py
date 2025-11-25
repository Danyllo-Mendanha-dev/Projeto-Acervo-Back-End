from django.urls import path
from . import views

app_name = 'exemplares' 

urlpatterns = [
    # (READ) /exemplares/
    path('', views.consultar_exemplares_view, name='exemplar_list'),
    
    # (CREATE) /exemplares/novo/
    path('novo/', views.cadastrar_exemplar_view, name='cadastrar_exemplar'),
    
    # (UPDATE) /exemplares/atualizar/5/
    path('atualizar/<int:pk>/', views.atualizar_exemplar_view, name='atualizar_exemplar'),
    
    # (DELETE) /exemplares/excluir/5/
    path('excluir/<int:pk>/', views.excluir_exemplar_view, name='excluir_exemplar'),
]
