from django.urls import path
from . import views

app_name = 'produtividade'

urlpatterns = [
    # Cadastros
    path('alunos/', views.StudentListView.as_view(), name='student_list'),
    path('alunos/novo/', views.StudentCreateView.as_view(), name='student_create'),
    path('alunos/<int:pk>/editar/', views.StudentUpdateView.as_view(), name='student_update'),

    path('grupos/', views.GroupListView.as_view(), name='group_list'),
    path('grupos/novo/', views.GroupCreateView.as_view(), name='group_create'),
    path('grupos/<int:pk>/editar/', views.GroupUpdateView.as_view(), name='group_update'),

    path('projetos/', views.ProjectListView.as_view(), name='project_list'),
    path('projetos/novo/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projetos/<int:pk>/editar/', views.ProjectUpdateView.as_view(), name='project_update'),

    # Lançamentos e relatórios
    path('lancamentos/<int:group_id>/', views.launch_productivity, name='launch_productivity'),
    path('relatorio/<int:group_id>/', views.GroupReportView.as_view(), name='group_report'),
    path('relatorio/<int:group_id>/pdf/', views.group_report_pdf, name='group_report_pdf'),
    path('relatorio/<int:group_id>/enviar/', views.send_report_email, name='send_report_email'),
]
