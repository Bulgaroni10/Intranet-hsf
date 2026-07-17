from django import forms

from usuarios.models import Setor
from .models import ImpressoraMonitorada


class ImpressoraMonitoradaForm(forms.ModelForm):
    class Meta:
        model = ImpressoraMonitorada
        fields = [
            'patrimonio', 'numero_serie', 'modelo_informado', 'situacao',
            'setor', 'local', 'ip', 'ativo',
        ]
        labels = {
            'modelo_informado': 'Modelo / driver informado',
            'local': 'Setor / local exibido no NOC',
            'ativo': 'Monitorar no NOC',
        }
        help_texts = {
            'ip': 'Opcional para estoque; obrigatório quando o monitoramento estiver ativo.',
            'modelo_informado': 'Ex.: Brother HL-L6202DW, Kyocera ou Ricoh.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['setor'].queryset = Setor.objects.filter(ativo=True).order_by('nome')

    def clean(self):
        dados = super().clean()
        setor = dados.get('setor')
        if setor and not dados.get('local'):
            dados['local'] = setor.nome
        if dados.get('ativo') and not dados.get('ip'):
            self.add_error('ip', 'Informe o IP para monitorar esta impressora no NOC.')
        if dados.get('situacao') != 'em_uso':
            dados['ativo'] = False
        return dados


class MovimentacaoImpressoraForm(forms.Form):
    situacao = forms.ChoiceField(choices=ImpressoraMonitorada.SITUACAO_CHOICES, label='Nova situação')
    setor = forms.ModelChoiceField(queryset=Setor.objects.none(), required=False)
    local = forms.CharField(max_length=180, required=False, label='Setor / local')
    ip = forms.GenericIPAddressField(required=False, label='Novo IP')
    monitorar_noc = forms.BooleanField(required=False, label='Monitorar no NOC')
    observacao = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['setor'].queryset = Setor.objects.filter(ativo=True).order_by('nome')

    def clean(self):
        dados = super().clean()
        if dados.get('monitorar_noc') and not dados.get('ip'):
            self.add_error('ip', 'Informe o IP para ativar o monitoramento no NOC.')
        if dados.get('situacao') != 'em_uso':
            dados['monitorar_noc'] = False
        setor = dados.get('setor')
        if setor and not dados.get('local'):
            dados['local'] = setor.nome
        return dados
