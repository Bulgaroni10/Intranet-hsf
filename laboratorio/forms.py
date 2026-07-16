from django import forms
from .models import ExameLaboratorial


class ExameForm(forms.ModelForm):
    class Meta:
        model = ExameLaboratorial
        fields = [
            'codigo', 'nome', 'categoria', 'sinonimos', 'material', 'recipiente',
            'volume_minimo', 'preparo', 'instrucoes_coleta', 'conservacao_transporte',
            'prazo_resultado', 'observacoes', 'ativo',
        ]
        widgets = {
            'preparo': forms.Textarea(attrs={'rows': 4}),
            'instrucoes_coleta': forms.Textarea(attrs={'rows': 4}),
            'conservacao_transporte': forms.Textarea(attrs={'rows': 4}),
            'observacoes': forms.Textarea(attrs={'rows': 4}),
        }
