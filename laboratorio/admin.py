from django.contrib import admin
from .models import DocumentoExame, ExameLaboratorial
class DocumentoInline(admin.TabularInline): model = DocumentoExame; extra = 0
@admin.register(ExameLaboratorial)
class ExameAdmin(admin.ModelAdmin):
    list_display = ('nome', 'codigo', 'unidade', 'categoria', 'material', 'ativo')
    list_filter = ('unidade', 'categoria', 'ativo'); search_fields = ('nome', 'codigo', 'sinonimos'); inlines = (DocumentoInline,)
