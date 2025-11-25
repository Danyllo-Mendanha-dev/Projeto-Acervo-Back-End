from django import forms
from django.db import connection

def get_livros_choices():
    """Busca todos os livros (obras) para usar como opções no formulário."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT id_livro, nome FROM Livro ORDER BY nome")
        choices = [(row[0], row[1]) for row in cursor.fetchall()]
        choices.insert(0, ('', '--- Selecione uma Obra ---'))
        return choices

class ExemplarForm(forms.Form):
    livro = forms.ChoiceField(
        label='Obra (Livro)',
        choices=[], 
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    numero_patrimonio = forms.IntegerField(
        label='Nº de Patrimônio',
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 123456'})
    )
    
    localizacao = forms.CharField(
        label='Localização na Prateleira',
        max_length=500, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Corredor B, Prateleira 3'})
    )
    
    dt_aquisicao = forms.DateField(
        label='Data de Aquisição',
        required=False,
        # ADICIONADA A CLASSE 'date-mask'
        widget=forms.DateInput(attrs={'class': 'form-control date-mask', 'type': 'text', 'placeholder': 'dd/mm/aaaa'})
    )

    dt_publicacao = forms.DateField(
        label='Data de Publicação (do exemplar)',
        required=False,
        # ADICIONADA A CLASSE 'date-mask'
        widget=forms.DateInput(attrs={'class': 'form-control date-mask', 'type': 'text', 'placeholder': 'dd/mm/aaaa'})
    )

    edicao = forms.CharField(
        label='Edição',
        max_length=300,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 5ª Edição, Revisada'})
    )

    def __init__(self, *args, **kwargs):
        """Sobrescreve o __init__ para preencher as 'choices' de livros."""
        super().__init__(*args, **kwargs)
        self.fields['livro'].choices = get_livros_choices()

