from django.db import models

class Group(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)

    def __str__(self):
        return self.nome

class Project(models.Model):
    titulo = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    grupo = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='projetos')
    orientador = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.titulo

class Student(models.Model):
    nome = models.CharField(max_length=120)
    turma = models.CharField(max_length=50)  # <— antes era email
    grupo = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, related_name='alunos')

    def __str__(self):
        return self.nome

class DailyEntry(models.Model):
    """
    Lançamento diário por aluno (0-10):
    - pontualidade
    - comunicacao
    - qualidade_codigo
    - entrega_tarefas
    - resolucao_problemas
    """
    data = models.DateField()
    aluno = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='entradas')
    grupo = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='entradas')
    projeto = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='entradas')

    pontualidade = models.PositiveSmallIntegerField(default=0)
    comunicacao = models.PositiveSmallIntegerField(default=0)
    qualidade_codigo = models.PositiveSmallIntegerField(default=0)
    entrega_tarefas = models.PositiveSmallIntegerField(default=0)
    resolucao_problemas = models.PositiveSmallIntegerField(default=0)

    observacoes = models.TextField(blank=True)

    class Meta:
        unique_together = ('data', 'aluno', 'projeto')

    def total(self):
        return sum([
            self.pontualidade,
            self.comunicacao,
            self.qualidade_codigo,
            self.entrega_tarefas,
            self.resolucao_problemas
        ]) / 5.0

    def __str__(self):
        return f"{self.data} - {self.aluno} ({self.grupo})"
