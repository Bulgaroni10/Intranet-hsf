from django import forms
from django.core.exceptions import ValidationError
import re

from usuarios.models import Setor
from .models import SolicitacaoAcesso


class SolicitacaoAcessoForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoAcesso
        fields = [
            'tipo', 'prioridade', 'colaborador_nome', 'cpf', 'tipo_conselho',
            'numero_conselho', 'uf_conselho', 'especialidade', 'setor',
            'cargo',
            'sistemas', 'justificativa',
            'data_necessaria',
        ]
        widgets = {
            'data_necessaria': forms.DateInput(attrs={'type': 'date'}),
            'sistemas': forms.Textarea(attrs={'rows': 5, 'placeholder': 'MV\nE-mail\nPasta de rede'}),
            'justificativa': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'colaborador_nome': 'Nome completo', 'cpf': 'CPF',
            'tipo_conselho': 'Conselho profissional',
            'numero_conselho': 'Número do conselho',
            'uf_conselho': 'UF do conselho', 'especialidade': 'Especialidade',
            'data_necessaria': 'Data necessária',
        }

    def clean_cpf(self):
        cpf = re.sub(r'\D', '', self.cleaned_data.get('cpf', ''))
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            raise ValidationError('Informe um CPF válido com 11 dígitos.')
        return cpf

    def clean_uf_conselho(self):
        uf = self.cleaned_data.get('uf_conselho', '').strip().upper()
        if uf and len(uf) != 2:
            raise ValidationError('Informe a UF com duas letras.')
        return uf

    def __init__(self, *args, unidade=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['setor'].queryset = Setor.objects.filter(ativo=True).order_by('nome')


class AtendimentoAcessoForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoAcesso
        fields = ['status', 'observacao_ti']
        widgets = {'observacao_ti': forms.Textarea(attrs={'rows': 5})}
