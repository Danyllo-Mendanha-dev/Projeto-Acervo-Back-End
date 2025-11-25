from django import forms
from django.db import connection

# --- FUNÇÕES HELPER (Consultas ao Banco) ---

def get_leitor_choices():
    """Busca todos os leitores para o cadastro de empréstimo."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT id_leitor, nome FROM Leitor ORDER BY nome")
        choices = [(row[0], row[1]) for row in cursor.fetchall()]
        choices.insert(0, ('', '--- Selecione um Leitor ---'))
        return choices

def get_exemplar_choices():
    """ 
    Busca exemplares DISPONÍVEIS (que não estão em empréstimos 'Em Andamento').
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT e.id_exemplar, l.nome, e.numero_patrimonio
            FROM Exemplar e
            JOIN Livro l ON e.id_livro = l.id_livro
            WHERE e.id_exemplar NOT IN (
                SELECT id_exemplar 
                FROM Emprestimo 
                WHERE status = 'Em Andamento'
            )
            ORDER BY l.nome
            """
        )
        choices = [(row[0], f"{row[1]} (Pat. {row[2]})") for row in cursor.fetchall()]
        choices.insert(0, ('', '--- Selecione um Exemplar Disponível ---'))
        return choices

# emprestimos/forms.py

def get_emprestimos_ativos_choices():
    """
    Busca todos os empréstimos 'Em Andamento' para o dropdown de DEVOLUÇÃO.
    Formatado como: 'Nome Leitor - Livro (Patrimônio)'
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 
                emp.id_emprestimo,
                l.nome AS livro_nome,
                le.nome AS leitor_nome,
                e.numero_patrimonio
            FROM Emprestimo emp
            JOIN Exemplar e ON emp.id_exemplar = e.id_exemplar
            JOIN Livro l ON e.id_livro = l.id_livro
            JOIN Leitor le ON emp.id_leitor = le.id_leitor
            WHERE emp.status = 'Em Andamento'
            ORDER BY le.nome, l.nome
            """
        )
        choices = [
            (row[0], f"{row[2]} - {row[1]} (Pat. {row[3]})") 
            for row in cursor.fetchall()
        ]
        
        return choices

# --- FORMS ---

class EmprestimoForm(forms.Form):
    """Formulário para CRIAR um novo empréstimo."""
    leitor = forms.ChoiceField(
        label='Leitor',
        choices=[],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    exemplar = forms.ChoiceField(
        label='Exemplar (apenas disponíveis)',
        choices=[], 
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['leitor'].choices = get_leitor_choices()
        self.fields['exemplar'].choices = get_exemplar_choices()


class DevolucaoForm(forms.Form):
    """Formulário para REGISTRAR A DEVOLUÇÃO (Update)."""
    multa = forms.DecimalField(
        label='Multa (R$)',
        required=False, # Lógica tratada no __init__
        initial=0.00,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.50'})
    )
    
    ocorrencia = forms.CharField(
        label='Ocorrência / Observações',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3, 
            'placeholder': 'Opcional: Descreva danos ou observações...'
        })
    )

    def __init__(self, *args, **kwargs):
        # Captura o argumento 'is_late' passado pela View
        is_late = kwargs.pop('is_late', False) 
        
        super().__init__(*args, **kwargs)

        if is_late:
            # CENÁRIO 1: Atrasado -> Multa visível e obrigatória
            self.fields['multa'].required = True
            self.fields['multa'].min_value = 0.01 
            self.fields['multa'].widget.attrs['placeholder'] = 'Informe o valor da multa'
            self.fields['multa'].error_messages = {
                'required': 'Como há atraso, o valor da multa é obrigatório (mesmo que simbólico).'
            }
        else:
            # CENÁRIO 2: No prazo -> Multa oculta e zerada
            # Mudamos o widget para HiddenInput para garantir que não apareça na tela
            self.fields['multa'].widget = forms.HiddenInput()
            self.fields['multa'].required = False
            self.fields['multa'].initial = 0.00