import csv
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from produtividade.models import Student

class Command(BaseCommand):
    help = (
        "Importa alunos a partir de um CSV com cabeçalho: Alunos,Turma. "
        "Exemplo: python manage.py import_alunos caminho\\alunos.csv"
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Caminho do arquivo CSV")
        parser.add_argument(
            "--delimiter", "-d", default=",",
            help="Delimitador do CSV (padrão: ','). Use ';' para CSVs com ponto e vírgula."
        )
        parser.add_argument(
            "--encoding", "-e", default="utf-8-sig",
            help="Encoding do arquivo (padrão: utf-8-sig)."
        )
        parser.add_argument(
            "--dedup", choices=["nome_turma", "nome"], default="nome_turma",
            help="Regra para evitar duplicados: 'nome_turma' (padrão) ou 'nome'."
        )

    def handle(self, *args, **opts):
        csv_path = Path(opts["csv_path"])
        delim = opts["delimiter"]
        enc = opts["encoding"]
        dedup = opts["dedup"]

        if not csv_path.exists():
            raise CommandError(f"Arquivo não encontrado: {csv_path}")

        # Lê CSV
        try:
            raw = csv_path.read_text(encoding=enc)
        except UnicodeDecodeError:
            raise CommandError("Falha ao decodificar o CSV. Tente --encoding utf-8 ou latin-1.")

        reader = csv.DictReader(raw.splitlines(), delimiter=delim)
        if not reader.fieldnames:
            raise CommandError("CSV sem cabeçalho. Esperado: Alunos,Turma")

        # Normaliza cabeçalhos
        header_map = { (h or "").strip().lower(): h for h in reader.fieldnames }
        # Aceita variações comuns
        nome_key = None
        for cand in ["alunos", "aluno", "nome", "name"]:
            if cand in header_map:
                nome_key = header_map[cand]
                break
        turma_key = None
        for cand in ["turma", "classe", "class"]:
            if cand in header_map:
                turma_key = header_map[cand]
                break

        if not nome_key or not turma_key:
            raise CommandError(
                f"Cabeçalho inválido. Precisa ter pelo menos 'Alunos' e 'Turma'. "
                f"Encontrado: {', '.join(reader.fieldnames)}"
            )

        criados = 0
        atualizados = 0
        ignorados = 0
        lidas = 0

        for row in reader:
            lidas += 1
            nome = (row.get(nome_key) or "").strip()
            turma = (row.get(turma_key) or "").strip()

            if not nome or not turma:
                ignorados += 1
                continue

            if dedup == "nome_turma":
                obj, created = Student.objects.update_or_create(
                    nome=nome, turma=turma, defaults={}
                )
            else:  # dedup == "nome"
                obj, created = Student.objects.update_or_create(
                    nome=nome, defaults={"turma": turma}
                )

            if created:
                criados += 1
            else:
                atualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f"Importação concluída: {lidas} linhas • {criados} criados • "
            f"{atualizados} existentes/atualizados • {ignorados} ignorados."
        ))
