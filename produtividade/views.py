# no topo do arquivo
import io, base64
from datetime import date, timedelta

import matplotlib
matplotlib.use('Agg')  # carrega 1x só
from matplotlib import pyplot as plt

from django.core.cache import cache
from django.db.models import Avg, F, FloatField, ExpressionWrapper



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
from django.db.models import Avg, F, FloatField, ExpressionWrapper

SCORE_EXPR = ExpressionWrapper(
    (F('pontualidade') + F('comunicacao') + F('qualidade_codigo') +
     F('entrega_tarefas') + F('resolucao_problemas')) / 5.0,
    output_field=FloatField()
)



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
# ---- Lançamento diário em lote por grupo ----
from datetime import date
from django.db.models import Avg, F, FloatField, ExpressionWrapper

@login_required
def launch_productivity(request, group_id):
    grupo = get_object_or_404(Group, pk=group_id)
    alunos = Student.objects.filter(grupo=grupo).order_by('nome')

    # Data escolhida (como objeto date)
    chosen_date_str = request.GET.get('data') or date.today().isoformat()
    try:
        chosen_date = date.fromisoformat(chosen_date_str)
    except ValueError:
        chosen_date = date.today()

    # Projeto selecionado (ou o primeiro do grupo)
    chosen_project_id = (
        request.GET.get('projeto')
        or Project.objects.filter(grupo=grupo).values_list('id', flat=True).first()
    )
    projeto_sel = Project.objects.filter(id=chosen_project_id).first() if chosen_project_id else None

    # Inicial do formset
    initial = []
    for aluno in alunos:
        entry = DailyEntry.objects.filter(aluno=aluno, grupo=grupo, data=chosen_date).first()
        item = {
            'aluno_id': aluno.id,
            'aluno_nome': aluno.nome,
            'data': chosen_date,            # pode ser date; o widget type=date renderiza ok
            'projeto': chosen_project_id
        }
        if entry:
            for f in CRITERIA_FIELDS:
                item[f] = getattr(entry, f)
            item['observacoes'] = entry.observacoes
            item['projeto'] = entry.projeto_id
        initial.append(item)

    formset = DailyEntryFormSet(initial=initial)

    # -------- NOVO: média histórica por aluno (0–10) --------
    # Base: todos os lançamentos do grupo (filtra por projeto se selecionado)
    base_qs = DailyEntry.objects.filter(grupo=grupo)
    if projeto_sel:
        base_qs = base_qs.filter(projeto=projeto_sel)

    # Média do registro = (5 critérios)/5.0
    score_expr = ExpressionWrapper(
        (F('pontualidade') + F('comunicacao') + F('qualidade_codigo') + F('entrega_tarefas') + F('resolucao_problemas')) / 5.0,
        output_field=FloatField()
    )

    medias_map = {}
    for a in alunos:
        val = base_qs.filter(aluno=a).aggregate(avg=Avg(score_expr))['avg']
        medias_map[a.id] = round(val, 2) if val is not None else None

    # Anexa a média em cada form (para o template exibir)
    for f in formset.forms:
        aid = f.initial.get('aluno_id')
        f.media_historico = medias_map.get(aid)

    # POST: salvar lançamentos
    if request.method == 'POST':
        formset = DailyEntryFormSet(request.POST)

        # reanexar médias para re-render em caso de erro
        for idx, f in enumerate(formset.forms):
            aid = request.POST.get(f'form-%d-aluno_id' % idx)
            f.media_historico = medias_map.get(int(aid)) if aid else None

        if formset.is_valid():
            for form in formset:
                aluno_id = form.cleaned_data['aluno_id']
                data_ = form.cleaned_data['data']              # date
                projeto = form.cleaned_data['projeto']
                valores = {f: form.cleaned_data[f] for f in CRITERIA_FIELDS}
                obs = form.cleaned_data.get('observacoes', '')
                aluno = Student.objects.get(pk=aluno_id)

                DailyEntry.objects.update_or_create(
                    aluno=aluno, grupo=grupo, data=data_, projeto=projeto,
                    defaults={**valores, 'observacoes': obs}
                )
            return redirect('produtividade:group_report', group_id=grupo.id)

    return render(request, 'produtividade/productivity_formset.html', {
        'grupo': grupo,
        'formset': formset,
        'data': chosen_date.isoformat(),
        'projetos': Project.objects.filter(grupo=grupo),
        'projeto_sel': projeto_sel,       # <-- para legenda da coluna
    })


# ---- Relatório (web) com Chart.js ----
# ---- Relatório (web) com filtros e nota geral ----
from django.db.models import Avg, F, FloatField, ExpressionWrapper

class GroupReportView(LoginRequiredMixin, TemplateView):
    template_name = 'produtividade/report.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        grupo = get_object_or_404(Group, pk=self.kwargs['group_id'])

        # --- filtros
        inicio_str = self.request.GET.get('inicio')
        fim_str    = self.request.GET.get('fim')
        dias_str   = (self.request.GET.get('dias') or '').strip()

        today = date.today()
        if inicio_str and fim_str:
            try:
                inicio = date.fromisoformat(inicio_str)
                fim    = date.fromisoformat(fim_str)
                if inicio > fim: inicio, fim = fim, inicio
            except ValueError:
                inicio, fim = today - timedelta(days=30), today
                dias_str = '30'
        else:
            try:
                dias = int(dias_str or 30)
            except ValueError:
                dias = 30
            inicio, fim = today - timedelta(days=dias), today
            dias_str = str(dias)

        aluno_sel = None
        aluno_id = self.request.GET.get('aluno')
        if aluno_id:
            aluno_sel = Student.objects.filter(id=aluno_id, grupo=grupo).first()

        # QS base com filtros aplicados (UMA VEZ)
        base_qs = DailyEntry.objects.filter(grupo=grupo, data__gte=inicio, data__lte=fim)
        if aluno_sel:
            base_qs = base_qs.filter(aluno=aluno_sel)

        # --- Nota geral média (1 query)
        nota_media_geral = base_qs.aggregate(avg=Avg(SCORE_EXPR))['avg'] or 0.0

        # --- Barras: média por aluno (1 query)
        # se houver filtro por aluno, o "agrupamento" retorna só ele.
        aluno_medias_qs = (base_qs
            .values('aluno__nome')
            .annotate(overall=Avg(SCORE_EXPR))
            .order_by('aluno__nome')
        )
        aluno_medias = [{'nome': r['aluno__nome'], 'overall': round(r['overall'] or 0, 2)}
                        for r in aluno_medias_qs]

        # --- Linha: média por dia (1 query)
        por_dia_qs = (base_qs
            .values('data')
            .annotate(media=Avg(SCORE_EXPR))
            .order_by('data')
        )
        por_dia_list = [{'data': r['data'].isoformat(), 'media': round(r['media'] or 0, 2)}
                        for r in por_dia_qs]

        ctx.update({
            'grupo': grupo,
            'alunos': Student.objects.filter(grupo=grupo).order_by('nome'),
            'aluno_sel': aluno_sel,
            'inicio': inicio.isoformat(),
            'fim': fim.isoformat(),
            'dias': dias_str,
            'aluno_medias': aluno_medias,
            'por_dia_list': por_dia_list,
            'nota_media_geral': round(nota_media_geral, 2),
            'serie_label': 'Média (filtro)',
        })
        return ctx


# ---- PDF (xhtml2pdf) com gráficos Matplotlib embutidos ----
@login_required
def group_report_pdf(request, group_id):
    from matplotlib import pyplot as plt
    import matplotlib
    matplotlib.use('Agg')
    from django.db.models import Avg, F, FloatField, ExpressionWrapper

    grupo = get_object_or_404(Group, pk=group_id)

    # --- filtros iguais aos do relatório web
    inicio_str = request.GET.get('inicio')
    fim_str    = request.GET.get('fim')
    dias_str   = request.GET.get('dias', '').strip()

    today = date.today()
    if inicio_str and fim_str:
        try:
            inicio = date.fromisoformat(inicio_str)
            fim    = date.fromisoformat(fim_str)
            if inicio > fim:
                inicio, fim = fim, inicio
        except ValueError:
            inicio = today - timedelta(days=30); fim = today
    else:
        try:
            dias = int(dias_str or 30)
        except ValueError:
            dias = 30
        inicio = today - timedelta(days=dias); fim = today

    aluno_sel = None
    aluno_id = request.GET.get('aluno')
    if aluno_id:
        try:
            aluno_sel = Student.objects.get(id=aluno_id, grupo=grupo)
        except Student.DoesNotExist:
            aluno_sel = None

    base_qs = DailyEntry.objects.filter(grupo=grupo, data__gte=inicio, data__lte=fim)
    if aluno_sel:
        base_qs = base_qs.filter(aluno=aluno_sel)

    # --- nota geral média
    from django.db.models import F, FloatField, ExpressionWrapper

# ... dentro de group_report_pdf, depois de definir base_qs ...

    score_expr = ExpressionWrapper(
        (F('pontualidade') + F('comunicacao') + F('qualidade_codigo') +
        F('entrega_tarefas') + F('resolucao_problemas')) / 5.0,
        output_field=FloatField()
    )

    entradas_qs = (base_qs
        .annotate(media_calc=score_expr)            # <<< anota a média por linha
        .select_related('aluno', 'projeto')
        .order_by('data', 'aluno__nome')
    )

    context = {
        'grupo': grupo,
        'inicio': inicio.isoformat(),
        'fim': fim.isoformat(),
        'nota_media_geral': round(nota_media_geral, 2),
        'bar_png_b64': bar_png_b64,
        'line_png_b64': line_png_b64,
        'entradas': entradas_qs,                    # <<< use a queryset anotada
    }

    # --- barras: média por aluno
    alunos_para_grafico = [aluno_sel] if aluno_sel else list(Student.objects.filter(grupo=grupo).order_by('nome'))
    aluno_overall = []
    for a in alunos_para_grafico:
        qs_a = base_qs.filter(aluno=a)
        if qs_a.exists():
            medias = qs_a.aggregate(
                pontualidade=Avg('pontualidade'),
                comunicacao=Avg('comunicacao'),
                qualidade_codigo=Avg('qualidade_codigo'),
                entrega_tarefas=Avg('entrega_tarefas'),
                resolucao_problemas=Avg('resolucao_problemas'),
            )
            overall = sum(medias.values()) / 5.0
            aluno_overall.append((a.nome, overall))

    bar_png_b64 = None
    if aluno_overall:
        nomes = [x[0] for x in aluno_overall]
        vals  = [x[1] for x in aluno_overall]
        plt.figure(figsize=(8,4))
        plt.bar(nomes, vals)
        plt.xticks(rotation=45, ha='right')
        plt.title('Média Geral por Aluno')
        plt.ylabel('Pontuação (0-10)')
        buf = io.BytesIO()
        plt.tight_layout(); plt.savefig(buf, format='png'); plt.close()
        bar_png_b64 = base64.b64encode(buf.getvalue()).decode('ascii')

    # --- linha: média (do filtro) por dia
    line_png_b64 = None
    day_map = {}
    for e in base_qs:
        day_map.setdefault(e.data, []).append(
            (e.pontualidade + e.comunicacao + e.qualidade_codigo + e.entrega_tarefas + e.resolucao_problemas) / 5.0
        )
    por_dia_sorted = sorted(day_map.items())
    if por_dia_sorted:
        dias_   = [d.isoformat() for d,_ in por_dia_sorted]
        medias_ = [round(sum(v)/len(v),2) for _,v in por_dia_sorted]
        plt.figure(figsize=(8,3.5))
        plt.plot(dias_, medias_, marker='o')
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Pontuação')
        plt.title('Evolução média (por dia)')
        buf2 = io.BytesIO()
        plt.tight_layout(); plt.savefig(buf2, format='png'); plt.close()
        line_png_b64 = base64.b64encode(buf2.getvalue()).decode('ascii')

    context = {
        'grupo': grupo,
        'dias': (fim - inicio).days + 1,
        'inicio': inicio.isoformat(),
        'fim': fim.isoformat(),
        'nota_media_geral': round(nota_media_geral, 2),
        'bar_png_b64': bar_png_b64,
        'line_png_b64': line_png_b64,
        'entradas': base_qs.select_related('aluno','projeto').order_by('data','aluno__nome'),
    }

    html = render_to_string('produtividade/report_pdf.html', context)
    from xhtml2pdf import pisa
    result = io.BytesIO()
    pdf_status = pisa.CreatePDF(src=html, dest=result, encoding='utf-8')
    if pdf_status.err:
        return HttpResponse('Erro ao gerar PDF', status=500)

    response = HttpResponse(result.getvalue(), content_type='application/pdf')
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

@login_required
def group_report_pdf_summary(request, group_id):
    grupo = get_object_or_404(Group, pk=group_id)

    # --- filtros iguais aos do relatório web
    inicio_str = request.GET.get('inicio')
    fim_str    = request.GET.get('fim')
    dias_str   = (request.GET.get('dias') or '').strip()

    today = date.today()
    if inicio_str and fim_str:
        try:
            inicio = date.fromisoformat(inicio_str)
            fim    = date.fromisoformat(fim_str)
            if inicio > fim: inicio, fim = fim, inicio
        except ValueError:
            inicio, fim = today - timedelta(days=30), today
    else:
        try:
            dias = int(dias_str or 30)
        except ValueError:
            dias = 30
        inicio, fim = today - timedelta(days=dias), today

    aluno_sel = None
    aluno_id = request.GET.get('aluno')
    if aluno_id:
        aluno_sel = Student.objects.filter(id=aluno_id, grupo=grupo).first()

    base_qs = DailyEntry.objects.filter(grupo=grupo, data__gte=inicio, data__lte=fim)
    if aluno_sel:
        base_qs = base_qs.filter(aluno=aluno_sel)

    # --- 1) Nota geral média
    nota_media_geral = base_qs.aggregate(avg=Avg(SCORE_EXPR))['avg'] or 0.0

    # --- 2) Médias por aluno (compacto)
    aluno_medias_qs = (base_qs
        .values('aluno__nome')
        .annotate(overall=Avg(SCORE_EXPR))
        .order_by('aluno__nome')
    )
    aluno_medias = [(r['aluno__nome'], float(r['overall'] or 0.0)) for r in aluno_medias_qs]

    # --- 3) Série por dia
    por_dia_qs = (base_qs
        .values('data')
        .annotate(media=Avg(SCORE_EXPR))
        .order_by('data')
    )
    serie_dias  = [r['data'].isoformat() for r in por_dia_qs]
    serie_medias= [round(float(r['media'] or 0.0), 2) for r in por_dia_qs]

    # --- Gráficos (PNG base64)
    bar_png_b64 = None
    if aluno_medias:
        nomes = [x[0] for x in aluno_medias]
        vals  = [x[1] for x in aluno_medias]
        # figura maior e com mais dpi para ficar nítido no PDF
        plt.figure(figsize=(10, 6), dpi=140)
        plt.bar(nomes, vals, color="#5179c2", edgecolor="#0F107A")  # vermelho da sua paleta
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Média (0–10)')
      
        buf = io.BytesIO()
        plt.tight_layout(); plt.savefig(buf, format='png'); plt.close()
        bar_png_b64 = base64.b64encode(buf.getvalue()).decode('ascii')

    line_png_b64 = None
    if serie_dias:
        plt.figure(figsize=(8, 3.2), dpi=110)
        plt.plot(serie_dias, serie_medias, marker='o')
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Média (0–10)')
        plt.title('Evolução média (por dia)')
        buf2 = io.BytesIO()
        plt.tight_layout(); plt.savefig(buf2, format='png'); plt.close()
        line_png_b64 = base64.b64encode(buf2.getvalue()).decode('ascii')
    

    # Observações por aluno (até 5 mais recentes)
    MAX_OBS_PER_STUDENT = 5
    obs_por_aluno_map = {}  # {nome: [ "YYYY-MM-DD: texto", ... ]}

    obs_qs = (base_qs
        .exclude(observacoes__isnull=True)
        .exclude(observacoes__exact='')
        .select_related('aluno')
        .values('aluno__nome', 'data', 'observacoes')
        .order_by('aluno__nome', '-data')
    )

    for row in obs_qs:
        nome = row['aluno__nome']
        lst  = obs_por_aluno_map.setdefault(nome, [])
        if len(lst) < MAX_OBS_PER_STUDENT:
            lst.append(f"{row['data'].isoformat()}: {row['observacoes']}")

    # Tabela final já unificada (nome, média, observações[])
    aluno_rows = [
        {'nome': nome, 'media': round(media, 2), 'obs_list': obs_por_aluno_map.get(nome, [])}
        for (nome, media) in aluno_medias
    ]

    # Ordena por nome e converte para lista de tuplas [(nome, [obs...]), ...]
    obs_por_aluno = sorted(obs_por_aluno_map.items(), key=lambda x: x[0])

    context = {
        'grupo': grupo,
        'inicio': inicio.isoformat(),
        'fim': fim.isoformat(),
        'nota_media_geral': round(nota_media_geral, 2),
        'bar_png_b64': bar_png_b64,
        'line_png_b64': line_png_b64,
        'aluno_rows': aluno_rows,   # << usar na tabela unificada
        # (se quiser pode remover 'aluno_medias' e 'obs_por_aluno' do context)
    }


    html = render_to_string('produtividade/report_pdf_summary.html', context)

    from xhtml2pdf import pisa
    result = io.BytesIO()
    pdf_status = pisa.CreatePDF(src=html, dest=result, encoding='utf-8')
    if pdf_status.err:
        return HttpResponse('Erro ao gerar PDF sintético', status=500)

    return HttpResponse(result.getvalue(), content_type='application/pdf')