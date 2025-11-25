from django.urls import path
from . import views

app_name = 'relatorios' 

urlpatterns = [
    # /relatorios/
    path('', views.relatorio_index_view, name='relatorio_index'),
    
    # /relatorios/leitores_atrasados/
    path('leitores_atrasados/', views.relatorio_leitores_atrasados_view, name='relatorio_leitores_atrasados'),
    
    # /relatorios/historico_livro/
    path('historico_livro/', views.relatorio_historico_livro_view, name='relatorio_historico_livro'),
    
    # /relatorios/livros_emprestados/
    path('livros_emprestados/', views.relatorio_livros_emprestados_view, name='relatorio_livros_emprestados'),
]
