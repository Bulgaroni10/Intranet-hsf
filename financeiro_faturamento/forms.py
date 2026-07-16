from django import forms
from django.contrib.auth import get_user_model

from .models import RegistroFinanceiro


class RegistroFinanceiroForm(forms.ModelForm):
    competencia = forms.DateField(
        input_formats=['%Y-%m', '%Y-%m-%d'],
        widget=forms.DateInput(attrs={'type': 'month'}, format='%Y-%m'),
        label='Competência',
    )
    class Meta:
        model = RegistroFinanceiro
        fields = [
            'area', 'tipo', 'titulo', 'competencia', 'prazo', 'entidade', 'valor',
            'prioridade', 'status', 'responsavel', 'descricao', 'observacao',
        ]
        widgets = {
            'prazo': forms.DateInput(attrs={'type': 'date'}),
            'descricao': forms.Textarea(attrs={'rows': 5}),
            'observacao': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, unidade=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsavel'].queryset = get_user_model().objects.filter(
            is_active=True, unidade=unidade,
        ).order_by('first_name', 'username') if unidade else get_user_model().objects.none()

    def clean_competencia(self):
        competencia = self.cleaned_data['competencia']
        return competencia.replace(day=1)
