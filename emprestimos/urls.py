from django.urls import path
from . import views

app_name = 'emprestimos' 

urlpatterns = [
    # (READ) /emprestimos/ (A lista principal)
    path('', views.consultar_emprestimos_view, name='emprestimo_list'),
    
    # (CREATE) /emprestimos/novo/
    path('novo/', views.cadastrar_emprestimo_view, name='cadastrar_emprestimo'),
    
    # (DEVOLUÇÃO)
    # /emprestimos/devolucao/ 
    path('devolucao/', views.registrar_devolucao_view, name='registrar_devolucao'),
    
    # (DELETE) /emprestimos/excluir/5/
    path('excluir/<int:pk>/', views.excluir_emprestimo_view, name='excluir_emprestimo'),
]
