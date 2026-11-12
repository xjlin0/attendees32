from django.core.management.base import BaseCommand
from attendees.persons.tasks import advance_grades


class Command(BaseCommand):
    help = (
        "Advance school grades by 1 for attendees in organizations with grade_converter configured. "
        "Capped at G12 (students at G12 or above will not be advanced)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "-o",
            "--organization",
            dest="organization_slug",
            type=str,
            default=None,
            help="Slug or ID of a specific organization to advance grades for.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate the grade advancement without saving any changes to the database.",
        )

    def handle(self, *args, **options):
        organization_slug = options.get("organization_slug") or options.get("organization")
        dry_run = options.get("dry_run", False)
        verbosity = options.get("verbosity", 1)

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Running in DRY-RUN mode. No changes will be committed to the database.\n")
            )

        # Calls the unified Celery periodic task directly
        result = advance_grades(
            organization_slug=organization_slug,
            dry_run=dry_run,
        )

        for org_info in result.get("organizations", []):
            org_name = org_info["name"]
            status = org_info["status"]
            if status == "skipped":
                if verbosity > 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[-] Organization '{org_name}' ({org_info['slug']}): Skipped ({org_info.get('reason')})"
                        )
                    )
            else:
                updated = org_info["updated_count"]
                capped = org_info["capped_count"]
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[+] Organization '{org_name}' ({org_info['slug']}): "
                        f"{updated} advanced, {capped} capped at/past G12."
                    )
                )
                if verbosity > 1:
                    for s in org_info.get("students", []):
                        self.stdout.write(
                            f"    * {s['name']}: {s['old_grade_name']} -> {s['new_grade_name']}"
                        )

        summary_msg = (
            f"\nFinished: {result['total_updated']} attendee(s) updated, "
            f"{result['total_capped']} capped at/past G12, "
            f"across {result['organizations_processed']} organization(s) "
            f"({result['organizations_skipped']} skipped)."
        )
        if dry_run:
            self.stdout.write(self.style.WARNING(f"[DRY-RUN] {summary_msg}"))
        else:
            self.stdout.write(self.style.SUCCESS(summary_msg))
