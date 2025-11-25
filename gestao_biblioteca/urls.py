# Em gestao_biblioteca/urls.py (crie este arquivo)
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('home/', views.home_view, name='home'),
    path('logout/', views.logout_view, name='logout'), 

    # --- Apps Modulares ---
    path('funcionarios/', include('funcionarios.urls')),
    path('leitores/', include('leitores.urls')),
    path('autores/', include('autores.urls')),
    path('livros/', include('livros.urls')),
    path('exemplares/', include('exemplares.urls')),
    path('relatorios/', include('relatorios.urls')),
    path('acervo/', include('acervo.urls')),     

    # --- NOVO APP ADICIONADO ---
    path('emprestimos/', include('emprestimos.urls')),
    
    # --- Páginas Restantes ---
    # As rotas de emprestimo foram removidas daqui
    path('relatorios/', views.relatorio_index_view, name='relatorio_index'),
]