"""Load (and optionally dump) the golden 350-member congregation.

    python manage.py load_golden_data --seed
    python manage.py load_golden_data --seed --dump fixtures/golden.json

The builder is deterministic: every UUID primary key comes from ``uuid5``, so
two runs against a freshly seeded database produce identical identifiers and
the dumped fixture diffs cleanly.  Dates are relative to *today* so ages and
"currently participating" windows stay true however long the fixture sits.
"""

import json
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from attendees.persons.models import Attendee
from attendees.tests.golden import PERSONA_PASSWORD, PERSONAS, build_golden_dataset


class Command(BaseCommand):
    help = "Load the golden test congregation on top of fixtures/db_seed.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--seed",
            action="store_true",
            help="load fixtures/db_seed.json first",
        )
        parser.add_argument(
            "--dump",
            metavar="PATH",
            help="after building, dumpdata the whole thing to PATH",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="build even though golden attendees already exist",
        )
        parser.add_argument(
            "--manifest",
            metavar="PATH",
            help=(
                "write a JSON map of golden key -> primary key to PATH, for "
                "callers outside Python (the Playwright suite reads this)"
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not options["force"] and Attendee.objects.filter(
            infos__names__original__icontains="Zhongxin"
        ).exists():
            raise CommandError(
                "golden data looks already loaded; pass --force to build anyway"
            )

        dataset = build_golden_dataset(load_seed=options["seed"])

        width = max(len(name) for name in dataset.counts)
        for name, count in dataset.counts.items():
            self.stdout.write(f"  {name.ljust(width)}  {count}")
        self.stdout.write(
            self.style.SUCCESS(
                f"golden dataset built: {dataset.counts['attendees']} live attendees"
            )
        )

        if options["manifest"]:
            manifest = {
                "counts": dataset.counts,
                "password": PERSONA_PASSWORD,
                "personas": {
                    persona.username: {
                        "groups": list(persona.groups),
                        "attendee": (
                            str(dataset.attendee(persona.attendee_key).id)
                            if persona.attendee_key
                            else None
                        ),
                    }
                    for persona in PERSONAS
                },
                "attendees": {
                    key: str(attendee.id)
                    for key, attendee in dataset.attendees.items()
                },
                "folks": {key: str(folk.id) for key, folk in dataset.folks.items()},
            }
            path = Path(options["manifest"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
            self.stdout.write(self.style.SUCCESS(f"manifest written to {path}"))

        if options["dump"]:
            call_command(
                "dumpdata",
                "--natural-foreign",
                "--natural-primary",
                "--indent",
                "1",
                "--exclude",
                "contenttypes",
                "--exclude",
                "auth.permission",
                "--output",
                options["dump"],
            )
            self.stdout.write(self.style.SUCCESS(f"dumped to {options['dump']}"))
