from django import forms

class AutorForm(forms.Form):
    nome = forms.CharField(
        label='Nome', 
        max_length=150, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    nacionalidade = forms.CharField(
        label='Nacionalidade', 
        max_length=100, 
        required=False,  # Definido como não obrigatório, como no seu template
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    biografia = forms.CharField(
        label='Biografia',
        required=False,  # Permite que o campo fique em branco
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}) # 'rows: 4' define a altura
    )