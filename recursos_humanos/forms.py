from django import forms

from usuarios.models import Setor
from .models import SolicitacaoRH


class SolicitacaoRHForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoRH
        fields = ['tipo', 'assunto', 'setor', 'telefone', 'descricao']
        widgets = {'descricao': forms.Textarea(attrs={'rows': 6})}

    def __init__(self, *args, **kwargs):
        kwargs.pop('unidade', None)
        super().__init__(*args, **kwargs)
        self.fields['setor'].queryset = Setor.objects.filter(ativo=True).order_by('nome')


class AtendimentoRHForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoRH
        fields = ['status', 'resposta_rh']
        widgets = {'resposta_rh': forms.Textarea(attrs={'rows': 6})}
