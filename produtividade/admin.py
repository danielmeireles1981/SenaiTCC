from django.contrib import admin
from .models import Group, Project, Student, DailyEntry

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'descricao')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'grupo', 'orientador')

# produtividade/admin.py
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'turma', 'grupo')  # <— troca email por turma
    list_filter = ('grupo', 'turma')                  # (opcional) filtrar por turma

@admin.register(DailyEntry)
class DailyEntryAdmin(admin.ModelAdmin):
    list_display = ('data', 'aluno', 'grupo', 'projeto', 'pontualidade', 'comunicacao',
                    'qualidade_codigo', 'entrega_tarefas', 'resolucao_problemas')
    list_filter = ('grupo', 'projeto', 'data')
    search_fields = ('aluno__nome',)
