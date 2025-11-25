from django.urls import path
from . import views

# Define um 'namespace' para este app. 
# Isso nos permite usar 'funcionarios:funcionario_list'
app_name = 'funcionarios' 

urlpatterns = [
    # (READ) 
    path('', views.consultar_funcionarios_view, name='funcionario_list'),
    
    # (CREATE)
    path('cadastrar/', views.cadastrar_funcionario_view, name='cadastrar_funcionario'),
    
    # (UPDATE)
    path('atualizar/<int:pk>/', views.atualizar_funcionario_view, name='atualizar_funcionario'),
    
    # (DELETE)
    path('excluir/<int:pk>/', views.excluir_funcionario_view, name='excluir_funcionario'),
]