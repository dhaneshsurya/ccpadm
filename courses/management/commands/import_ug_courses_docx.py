from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from courses.docx_import import import_ug_courses_from_docx


class Command(BaseCommand):
    help = 'Import UG first-semester programs and courses from the college Word document.'

    def add_arguments(self, parser):
        parser.add_argument(
            'docx_path',
            nargs='?',
            default=r'C:\Users\LEGION\Downloads\UG First Semester  Course Information Dec 2025.docx',
            help='Path to the UG course information .docx file',
        )
        parser.add_argument(
            '--replace-ug',
            action='store_true',
            help='Delete existing courses for UG programs in the document before import',
        )

    def handle(self, *args, **options):
        docx_path = Path(options['docx_path'])
        if not docx_path.exists():
            raise CommandError(f'File not found: {docx_path}')

        stats = import_ug_courses_from_docx(
            docx_path,
            replace_existing_ug=options['replace_ug'],
        )
        self.stdout.write(
            self.style.SUCCESS(
                'Import complete: '
                f"{stats['rows_parsed']} rows parsed, "
                f"{stats['programs_created']} programs created, "
                f"{stats['programs_updated']} programs updated, "
                f"{stats['courses_created']} courses created, "
                f"{stats['courses_updated']} courses updated, "
                f"{stats.get('programs_removed', 0)} duplicate programs removed, "
                f"{stats.get('legacy_courses_removed', 0)} legacy courses removed."
            )
        )