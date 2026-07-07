from django import forms

from .models import SolicitacaoInterna, ComentarioSolicitacao


class SolicitacaoInternaForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoInterna
        fields = [
            'titulo',
            'categoria',
            'prioridade',
            'descricao',
        ]

        widgets = {
            'titulo': forms.TextInput(attrs={
                'placeholder': 'Ex: Solicitação de manutenção, cadastro, documento...'
            }),
            'descricao': forms.Textarea(attrs={
                'rows': 6,
                'placeholder': 'Descreva a solicitação com o máximo de detalhes.'
            }),
        }


class AtendimentoSolicitacaoForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoInterna
        fields = [
            'status',
            'prioridade',
            'responsavel',
        ]


class ComentarioSolicitacaoForm(forms.ModelForm):
    class Meta:
        model = ComentarioSolicitacao
        fields = ['mensagem']

        widgets = {
            'mensagem': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Digite uma atualização, orientação ou resposta...'
            }),
        }