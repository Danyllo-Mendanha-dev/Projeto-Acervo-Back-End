from django import forms
from django.db import connection

def get_autores_choices():
    """Busca todos os autores no banco para usar como opções no formulário."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT id_autor, nome FROM Autor ORDER BY nome")
        # Formata como uma lista de tuplas: [(id, nome), (id, nome), ...]
        return [(row[0], row[1]) for row in cursor.fetchall()]

class LivroForm(forms.Form):
    nome = forms.CharField(
        label='Título da Obra', 
        max_length=200, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    isbn = forms.CharField(
        label='ISBN (13 dígitos)', 
        max_length=13, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    genero = forms.CharField(
        label='Gênero/Categoria', 
        max_length=100, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    qtde_exemplares = forms.IntegerField(
        label='Quantidade de Exemplares',
        initial=0, # Valor inicial
        min_value=0, # Não permite números negativos
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    status = forms.ChoiceField(
        label='Status',
        choices=[
            # Você pode ajustar estas opções conforme sua necessidade
            ('Disponível', 'Disponível'),
            ('Emprestado', 'Emprestado'),
            ('Manutenção', 'Manutenção'),
            ('Descartado', 'Descartado'),
        ],
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # --- Campo de Múltipla Escolha para os Autores ---
    autores = forms.MultipleChoiceField(
        label='Autores',
        required=True,
        # Usamos CheckboxSelectMultiple para renderizar como uma lista de caixas
        widget=forms.CheckboxSelectMultiple,
        choices=[] # As escolhas serão preenchidas dinamicamente
    )

    def __init__(self, *args, **kwargs):
        """Sobrescreve o __init__ para preencher as 'choices' de autores."""
        super().__init__(*args, **kwargs)
        # Preenche o campo 'autores' com os dados buscados do banco
        self.fields['autores'].choices = get_autores_choices()