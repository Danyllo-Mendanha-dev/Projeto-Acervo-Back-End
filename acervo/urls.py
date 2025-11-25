from django.urls import path
from . import views

app_name = 'acervo' 

urlpatterns = [
    # /acervo/
    path('', views.acervo_view, name='acervo_index'),
]
