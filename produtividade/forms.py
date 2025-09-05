# produtividade/forms.py
from django import forms
from django.forms import formset_factory
from .models import Student, Group, Project

INPUT_CSS = "input-field"

class BaseStyledForm(forms.ModelForm):
    """Aplica class='input-field' a todos os widgets automaticamente."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            # preserva classes existentes e acrescenta input-field
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " " + INPUT_CSS).strip()

# produtividade/forms.py
class StudentForm(BaseStyledForm):
    class Meta:
        model = Student
        fields = ['nome', 'turma', 'grupo']  # <— antes: 'email'
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Nome do aluno'}),
            'turma': forms.TextInput(attrs={'placeholder': 'Turma (ex.: 3ºA Info)'}),
            'grupo': forms.Select(),
        }


class GroupForm(BaseStyledForm):
    class Meta:
        model = Group
        fields = ['nome', 'descricao']
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Nome do grupo'}),
            'descricao': forms.Textarea(attrs={'placeholder': 'Descrição do grupo', 'rows': 3}),
        }

class ProjectForm(BaseStyledForm):
    class Meta:
        model = Project
        fields = ['titulo', 'descricao', 'grupo', 'orientador']
        widgets = {
            'titulo': forms.TextInput(attrs={'placeholder': 'Título do projeto'}),
            'descricao': forms.Textarea(attrs={'placeholder': 'Resumo/escopo do projeto', 'rows': 3}),
            'grupo': forms.Select(),
            'orientador': forms.TextInput(attrs={'placeholder': 'Nome do orientador'}),
        }

CRITERIA_FIELDS = ['pontualidade', 'comunicacao', 'qualidade_codigo', 'entrega_tarefas', 'resolucao_problemas']

class DailyEntryItemForm(forms.Form):
    aluno_id = forms.IntegerField(widget=forms.HiddenInput())
    aluno_nome = forms.CharField(disabled=True, required=False, label='Aluno',
                                 widget=forms.TextInput(attrs={'class': INPUT_CSS}))

    data = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': INPUT_CSS})
    )
    projeto = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        widget=forms.Select(attrs={'class': INPUT_CSS})
    )

    pontualidade = forms.IntegerField(min_value=0, max_value=10, initial=0,
        widget=forms.NumberInput(attrs={'class': INPUT_CSS, 'placeholder': '0–10'}))
    comunicacao = forms.IntegerField(min_value=0, max_value=10, initial=0,
        widget=forms.NumberInput(attrs={'class': INPUT_CSS, 'placeholder': '0–10'}))
    qualidade_codigo = forms.IntegerField(min_value=0, max_value=10, initial=0, label='Qualidade do Código',
        widget=forms.NumberInput(attrs={'class': INPUT_CSS, 'placeholder': '0–10'}))
    entrega_tarefas = forms.IntegerField(min_value=0, max_value=10, initial=0, label='Entrega de Tarefas',
        widget=forms.NumberInput(attrs={'class': INPUT_CSS, 'placeholder': '0–10'}))
    resolucao_problemas = forms.IntegerField(min_value=0, max_value=10, initial=0, label='Resolução de Problemas',
        widget=forms.NumberInput(attrs={'class': INPUT_CSS, 'placeholder': '0–10'}))
    observacoes = forms.CharField(required=False,
        widget=forms.Textarea(attrs={'class': INPUT_CSS, 'rows': 2, 'placeholder': 'Observações'}))

DailyEntryFormSet = formset_factory(DailyEntryItemForm, extra=0)
