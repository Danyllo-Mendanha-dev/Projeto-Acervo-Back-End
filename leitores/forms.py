from django import forms
# Importe o campo específico para CPF do Brasil
from localflavor.br.forms import BRCPFField

class LeitorForm(forms.Form):
    nome = forms.CharField(label='Nome Completo', required=True, max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(label='Email', required=True, max_length=100, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    
    # --- MUDANÇA AQUI: Usando BRCPFField ---
    cpf = BRCPFField(
        label='CPF', 
        required=True, # CPF obrigatório para identificar unicamente o leitor
        widget=forms.TextInput(attrs={'class': 'form-control cpf-mask', 'placeholder': '000.000.000-00'}),
        
        error_messages={
            'invalid': 'CPF inválido. Por favor, verifique os números digitados.',
            'max_digits': 'Este campo requer 11 dígitos.',
            'digits_only': 'Este campo requer apenas números.',
            'required': 'O campo CPF é obrigatório.'
        }
    )
    # ---------------------------------------

    telefone = forms.CharField(label='Telefone', max_length=20, 
    required=True, widget=forms.TextInput(attrs={'class': 'form-control phone-mask',  # Adicionei 'phone-mask'
    'placeholder': '(00) 00000-0000'}))

    data_nascimento = forms.DateField(
        label='Data de Nascimento', 
        required=False, 
        # ADICIONADA A CLASSE 'date-mask'
        widget=forms.DateInput(attrs={'class': 'form-control date-mask', 'type': 'text', 'placeholder': 'dd/mm/aaaa'}),
    )
    
    endereco = forms.CharField(label='Endereço', max_length=200, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))

    def clean_cpf(self):
        """Remove pontos e traço do CPF antes de validar/salvar."""
        cpf = self.cleaned_data['cpf']
        return cpf.replace(".", "").replace("-", "")