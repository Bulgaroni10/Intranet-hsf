import re

from django import forms
from django.core.exceptions import ValidationError

from usuarios.models import Setor
from .models import SolicitacaoAcessoRemoto


class SolicitacaoAcessoRemotoForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoAcessoRemoto
        fields = [
            'nome', 'cpf', 'email', 'telefone', 'vinculo', 'empresa_terceira',
            'setor', 'tipo_acesso', 'equipamento', 'sistema_destino', 'finalidade',
            'inicio_validade', 'fim_validade',
        ]
        widgets = {
            'inicio_validade': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'fim_validade': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'finalidade': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, unidade=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['setor'].queryset = Setor.objects.filter(ativo=True).order_by('nome')

    def clean_cpf(self):
        cpf = re.sub(r'\D', '', self.cleaned_data.get('cpf', ''))
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            raise ValidationError('Informe um CPF válido com 11 dígitos.')
        return cpf

    def clean(self):
        dados = super().clean()
        if dados.get('vinculo') == 'terceiro' and not dados.get('empresa_terceira'):
            self.add_error('empresa_terceira', 'Informe a empresa do terceiro.')
        inicio, fim = dados.get('inicio_validade'), dados.get('fim_validade')
        if inicio and fim and fim <= inicio:
            self.add_error('fim_validade', 'O término deve ser posterior ao início.')
        return dados


class AtendimentoAcessoRemotoForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoAcessoRemoto
        fields = ['status', 'observacao_ti']
        widgets = {'observacao_ti': forms.Textarea(attrs={'rows': 5})}
