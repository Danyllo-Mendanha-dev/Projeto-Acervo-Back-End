from django.urls import path
from . import views

app_name = 'autores'

urlpatterns = [
    # READ (ex: /autores/)
    path('', views.consultar_autores_view, name='autor_list'),
    
    # CREATE (ex: /autores/cadastrar/)
    path('cadastrar/', views.cadastrar_autor_view, name='cadastrar_autor'),
    
    # UPDATE (ex: /autores/atualizar/1/)
    path('atualizar/<int:pk>/', views.atualizar_autor_view, name='atualizar_autor'),
    
    # DELETE (ex: /autores/excluir/1/)
    path('excluir/<int:pk>/', views.excluir_autor_view, name='excluir_autor'),
]
