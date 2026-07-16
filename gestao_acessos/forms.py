from django import forms

from usuarios.models import Setor
from .models import SolicitacaoAcesso


class SolicitacaoAcessoForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoAcesso
        fields = [
            'tipo', 'prioridade', 'colaborador_nome', 'colaborador_matricula',
            'colaborador_cargo', 'setor', 'sistemas', 'justificativa',
            'data_necessaria',
        ]
        widgets = {
            'data_necessaria': forms.DateInput(attrs={'type': 'date'}),
            'sistemas': forms.Textarea(attrs={'rows': 5, 'placeholder': 'MV\nE-mail\nPasta de rede'}),
            'justificativa': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, unidade=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['setor'].queryset = Setor.objects.filter(ativo=True).order_by('nome')


class AtendimentoAcessoForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoAcesso
        fields = ['status', 'observacao_ti']
        widgets = {'observacao_ti': forms.Textarea(attrs={'rows': 5})}
