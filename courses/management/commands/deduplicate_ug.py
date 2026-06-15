from django.core.management.base import BaseCommand

from courses.deduplicate import deduplicate_ug_programs_and_courses


class Command(BaseCommand):
    help = 'Remove legacy duplicate UG program names and their duplicate course rows.'

    def handle(self, *args, **options):
        stats = deduplicate_ug_programs_and_courses()
        self.stdout.write(
            self.style.SUCCESS(
                'UG deduplication complete: '
                f"{stats['programs_removed']} program(s) removed, "
                f"{stats['courses_removed']} legacy course row(s) removed, "
                f"{stats['courses_deduped']} in-program duplicate(s) removed, "
                f"{stats.get('bsc_courses_merged', 0)} course(s) merged into B.Sc., "
                f"{stats['students_migrated']} student(s) migrated, "
                f"{stats['admissions_migrated']} admission(s) migrated."
            )
        )