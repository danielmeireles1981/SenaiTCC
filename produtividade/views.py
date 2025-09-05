from datetime import date, timedelta
import io, base64
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, TemplateView
from django.conf import settings
from django.core.mail import EmailMessage

from .models import Student, Group, Project, DailyEntry
from .forms import StudentForm, GroupForm, ProjectForm, DailyEntryFormSet, CRITERIA_FIELDS

from datetime import date, timedelta
import io, base64
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.db.models import Avg
from .models import Student, Group, Project, DailyEntry


# ---- Cadastros (CBVs) ----
class StudentListView(LoginRequiredMixin, ListView):
    model = Student
    template_name = 'produtividade/student_list.html'
    context_object_name = 'alunos'

class StudentCreateView(LoginRequiredMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = 'produtividade/form.html'
    success_url = reverse_lazy('produtividade:student_list')

class StudentUpdateView(LoginRequiredMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = 'produtividade/form.html'
    success_url = reverse_lazy('produtividade:student_list')

class GroupListView(LoginRequiredMixin, ListView):
    model = Group
    template_name = 'produtividade/group_list.html'
    context_object_name = 'grupos'

class GroupCreateView(LoginRequiredMixin, CreateView):
    model = Group
    form_class = GroupForm
    template_name = 'produtividade/form.html'
    success_url = reverse_lazy('produtividade:group_list')

class GroupUpdateView(LoginRequiredMixin, UpdateView):
    model = Group
    form_class = GroupForm
    template_name = 'produtividade/form.html'
    success_url = reverse_lazy('produtividade:group_list')

class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = 'produtividade/project_list.html'
    context_object_name = 'projetos'

class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'produtividade/form.html'
    success_url = reverse_lazy('produtividade:project_list')

class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'produtividade/form.html'
    success_url = reverse_lazy('produtividade:project_list')

# ---- Lançamento diário em lote por grupo ----
@login_required
def launch_productivity(request, group_id):
    grupo = get_object_or_404(Group, pk=group_id)
    alunos = Student.objects.filter(grupo=grupo).order_by('nome')
    initial = []
    chosen_date = request.GET.get('data') or date.today().isoformat()
    chosen_project_id = request.GET.get('projeto') or Project.objects.filter(grupo=grupo).values_list('id', flat=True).first()

    for aluno in alunos:
        entry = DailyEntry.objects.filter(aluno=aluno, grupo=grupo, data=chosen_date).first()
        initial_item = {
            'aluno_id': aluno.id,
            'aluno_nome': aluno.nome,
            'data': chosen_date,
            'projeto': chosen_project_id
        }
        if entry:
            for f in CRITERIA_FIELDS:
                initial_item[f] = getattr(entry, f)
            initial_item['observacoes'] = entry.observacoes
            initial_item['projeto'] = entry.projeto_id
        initial.append(initial_item)

    formset = DailyEntryFormSet(initial=initial)
    if request.method == 'POST':
        formset = DailyEntryFormSet(request.POST)
        if formset.is_valid():
            for form in formset:
                aluno_id = form.cleaned_data['aluno_id']
                data_ = form.cleaned_data['data']
                projeto = form.cleaned_data['projeto']
                valores = { f: form.cleaned_data[f] for f in CRITERIA_FIELDS }
                obs = form.cleaned_data.get('observacoes', '')
                aluno = Student.objects.get(pk=aluno_id)

                DailyEntry.objects.update_or_create(
                    aluno=aluno, grupo=grupo, data=data_, projeto=projeto,
                    defaults = {**valores, 'observacoes': obs}
                )
            return redirect('produtividade:group_report', group_id=grupo.id)

    return render(request, 'produtividade/productivity_formset.html', {
        'grupo': grupo, 'formset': formset, 'data': chosen_date,
        'projetos': Project.objects.filter(grupo=grupo)
    })

# ---- Relatório (web) com Chart.js ----
class GroupReportView(LoginRequiredMixin, TemplateView):
    template_name = 'produtividade/report.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        group_id = self.kwargs['group_id']
        grupo = get_object_or_404(Group, pk=group_id)

        try:
            dias = int(self.request.GET.get('dias', 30))
        except Exception:
            dias = 30
        start_date = date.today() - timedelta(days=dias)

        # Médias por aluno
        alunos = Student.objects.filter(grupo=grupo)
        aluno_medias = []
        for a in alunos:
            qs = DailyEntry.objects.filter(aluno=a, grupo=grupo, data__gte=start_date)
            if qs.exists():
                medias = qs.aggregate(
                    pontualidade=Avg('pontualidade'),
                    comunicacao=Avg('comunicacao'),
                    qualidade_codigo=Avg('qualidade_codigo'),
                    entrega_tarefas=Avg('entrega_tarefas'),
                    resolucao_problemas=Avg('resolucao_problemas')
                )
                overall = sum(medias.values()) / 5.0
                aluno_medias.append({'nome': a.nome, 'overall': round(overall, 2)})

        # Média do grupo por dia
        day_map = {}
        for e in DailyEntry.objects.filter(grupo=grupo, data__gte=start_date):
            day_map.setdefault(e.data, []).append(e.total())
        por_dia_list = [{'data': d.isoformat(), 'media': round(sum(vals)/len(vals),2)} for d, vals in sorted(day_map.items())]

        ctx.update({
            'grupo': grupo,
            'aluno_medias': aluno_medias,
            'por_dia_list': por_dia_list,
            'dias': dias,
        })
        return ctx

# ---- PDF (xhtml2pdf) com gráficos Matplotlib embutidos ----
@login_required
def group_report_pdf(request, group_id):
    # Gera os gráficos e contexto como você já fazia
    from matplotlib import pyplot as plt
    import matplotlib
    matplotlib.use('Agg')

    grupo = get_object_or_404(Group, pk=group_id)
    try:
        dias = int(request.GET.get('dias', 30))
    except Exception:
        dias = 30
    start_date = date.today() - timedelta(days=dias)

    alunos = Student.objects.filter(grupo=grupo)
    aluno_overall = []
    for a in alunos:
        qs = DailyEntry.objects.filter(aluno=a, grupo=grupo, data__gte=start_date)
        if qs.exists():
            medias = qs.aggregate(
                pontualidade=Avg('pontualidade'),
                comunicacao=Avg('comunicacao'),
                qualidade_codigo=Avg('qualidade_codigo'),
                entrega_tarefas=Avg('entrega_tarefas'),
                resolucao_problemas=Avg('resolucao_problemas')
            )
            overall = sum(medias.values()) / 5.0
            aluno_overall.append((a.nome, overall))

    # gráfico barras
    bar_png_b64 = None
    if aluno_overall:
        nomes = [x[0] for x in aluno_overall]
        vals = [x[1] for x in aluno_overall]
        plt.figure(figsize=(8,4))
        plt.bar(nomes, vals)
        plt.xticks(rotation=45, ha='right')
        plt.title('Média Geral por Aluno')
        plt.ylabel('Pontuação (0-10)')
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png')
        plt.close()
        bar_png_b64 = base64.b64encode(buf.getvalue()).decode('ascii')

    # linha (média do grupo por dia)
    day_map = {}
    for e in DailyEntry.objects.filter(grupo=grupo, data__gte=start_date):
        day_map.setdefault(e.data, []).append(e.total())
    por_dia_sorted = sorted(day_map.items())
    line_png_b64 = None
    if por_dia_sorted:
        dias_ = [d.isoformat() for d,_ in por_dia_sorted]
        medias_ = [round(sum(v)/len(v),2) for _,v in por_dia_sorted]
        plt.figure(figsize=(8,3.5))
        plt.plot(dias_, medias_, marker='o')
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Pontuação')
        plt.title('Evolução Média do Grupo (por dia)')
        plt.tight_layout()
        buf2 = io.BytesIO()
        plt.savefig(buf2, format='png')
        plt.close()
        line_png_b64 = base64.b64encode(buf2.getvalue()).decode('ascii')

    context = {
        'grupo': grupo,
        'dias': dias,
        'bar_png_b64': bar_png_b64,
        'line_png_b64': line_png_b64,
        'entradas': DailyEntry.objects.filter(grupo=grupo, data__gte=start_date)
                                     .select_related('aluno','projeto')
                                     .order_by('data','aluno__nome'),
    }

    html = render_to_string('produtividade/report_pdf.html', context)

    # --- xhtml2pdf: passe a STRING direto; grave em BytesIO ---
    from xhtml2pdf import pisa
    result = io.BytesIO()
    pdf_status = pisa.CreatePDF(src=html, dest=result, encoding='utf-8')

    if pdf_status.err:
        # Opcional: log para ver o que deu ruim
        # print(pdf_status.log)  # cuidado em prod
        return HttpResponse('Erro ao gerar PDF', status=500)

    pdf_bytes = result.getvalue()
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename=relatorio_{grupo.nome}.pdf'
    return response

# ---- Enviar PDF por e-mail para coordenação ----
@login_required
def send_report_email(request, group_id):
    grupo = get_object_or_404(Group, pk=group_id)
    pdf_response = group_report_pdf(request, group_id)
    if pdf_response.status_code != 200:
        return pdf_response

    pdf_bytes = pdf_response.content
    subject = f'Relatório de Produtividade - Grupo {grupo.nome}'
    body = 'Segue em anexo o relatório de produtividade do grupo.'
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email='nao-responder@example.com',
        to=getattr(settings, 'COORDINATION_EMAILS', ['coordenacao@example.com'])
    )
    email.attach(f'relatorio_{grupo.nome}.pdf', pdf_bytes, 'application/pdf')
    email.send(fail_silently=False)
    return redirect('produtividade:group_report', group_id=grupo.id)
