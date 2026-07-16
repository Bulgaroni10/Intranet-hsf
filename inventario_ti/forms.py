from django import forms

from usuarios.models import Setor
from .models import ImpressoraMonitorada


class ImpressoraMonitoradaForm(forms.ModelForm):
    class Meta:
        model = ImpressoraMonitorada
        fields = ['ip', 'modelo_informado', 'setor', 'local', 'ativo']
        labels = {
            'modelo_informado': 'Modelo / driver informado',
            'local': 'Setor / local exibido no NOC',
        }
        help_texts = {
            'ip': 'Informe o IP fixo da impressora.',
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
        return dados
