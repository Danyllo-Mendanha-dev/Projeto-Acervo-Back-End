from django.urls import path
from . import views

# Define um 'namespace' para este app. 
app_name = 'livros' 

urlpatterns = [
    # (READ) /livros/
    path('', views.consultar_livros_view, name='livro_list'),
    
    # (CREATE) /livros/novo/
    path('novo/', views.cadastrar_livro_view, name='cadastrar_livro'),
    
    # (UPDATE) /livros/atualizar/5/
    path('atualizar/<int:pk>/', views.atualizar_livro_view, name='atualizar_livro'),
    
    # (DELETE) /livros/excluir/5/
    path('excluir/<int:pk>/', views.excluir_livro_view, name='excluir_livro'),
]
