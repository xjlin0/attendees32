"""
Provision everything the Tally check-in app needs to talk to this server.

Tally is a server-to-server client: it reads the roster over the JSON API with
a DRF token, creates quick-added visitors as attendees, keeps profile edits in
sync, and imports attendance history. This command creates (or finds) the
pieces that integration stands on, idempotently — run it again and it changes
nothing that already exists, so it doubles as the way to look the values up.

    python manage.py setup_tally_integration --organization-slug cfcch

It prints, at the end, exactly the values to copy into Tally's configuration
(A32_DIVISION_ID, A32_MEET_SLUG, …) plus the token — the token only on the run
that created it; DRF stores it retrievably, so later runs print it again by
design (it is the *server's* secret store, unlike hashed passwords).
"""
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from rest_framework.authtoken.models import Token

from attendees.occasions.models import Assembly, Character, Meet
from attendees.persons.models import Attendee, Category, Relation, Utility
from attendees.users.models import User
from attendees.whereabouts.models import Division, Organization


class Command(BaseCommand):
    help = "Provision the Tally integration: division/assembly/meet/character, integration user, group and DRF token."

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-slug",
            required=True,
            help="The organization Tally connects to. Must already exist.",
        )
        parser.add_argument("--division-slug", default=None, help="Created if absent. Default: <org-slug>_tally_youth")
        parser.add_argument("--assembly-slug", default=None, help="Created if absent. Default: <org-slug>_tally_youth_ministry")
        parser.add_argument("--meet-slug", default=None, help="Created if absent. Default: <org-slug>_tally_gathering")
        parser.add_argument("--character-slug", default=None, help="Created if absent. Default: <org-slug>_tally_student")
        parser.add_argument("--username", default="tally-integration", help="The integration user.")
        parser.add_argument("--group", default="tally_integration", help="The auth group granted to the user.")

    @transaction.atomic
    def handle(self, *args, **options):
        org_slug = options["organization_slug"]
        organization = Organization.objects.filter(slug=org_slug).first()
        if organization is None:
            known = ", ".join(Organization.objects.values_list("slug", flat=True)) or "(none)"
            raise CommandError(f"No organization with slug '{org_slug}'. Known: {known}")

        # Tally resolves these by title when it files people into families —
        # they come from the canonical seed, not from this command, because a
        # half-made relation vocabulary is worse than a missing one.
        for title in ("child", "parent"):
            if not Relation.objects.filter(title=title).exists():
                raise CommandError(
                    f"Relation '{title}' is missing. Load the seed vocabulary first: "
                    "python manage.py loaddata fixtures/db_seed.json"
                )
        # Creating the integration attendee fires the post-save signal, which
        # needs the hidden role and the non-family folk category.
        if not Relation.objects.filter(pk=Attendee.HIDDEN_ROLE).exists():
            raise CommandError(
                "The hidden relation (pk 0) is missing. Load the seed vocabulary first: "
                "python manage.py loaddata fixtures/db_seed.json"
            )
        if not Category.objects.filter(pk=Attendee.NON_FAMILY_CATEGORY).exists():
            raise CommandError(
                "The non-family folk category is missing. Load the seed vocabulary first: "
                "python manage.py loaddata fixtures/db_seed.json"
            )
        if not Category.objects.filter(pk=Attendee.FAMILY_CATEGORY).exists():
            raise CommandError(
                "The family folk category is missing. Load the seed vocabulary first: "
                "python manage.py loaddata fixtures/db_seed.json"
            )

        division_slug = options["division_slug"] or f"{org_slug}_tally_youth"
        assembly_slug = options["assembly_slug"] or f"{org_slug}_tally_youth_ministry"
        meet_slug = options["meet_slug"] or f"{org_slug}_tally_gathering"
        character_slug = options["character_slug"] or f"{org_slug}_tally_student"

        group, group_created = Group.objects.get_or_create(name=options["group"])
        self.note("auth group", group.name, group_created)

        division = Division.objects.filter(slug=division_slug).first()
        if division is None:
            division = Division.objects.create(
                organization=organization,
                slug=division_slug,
                display_name="Youth",
                audience_auth_group=group,
                infos={},
            )
            self.note("division", division.slug, True)
        else:
            self.note("division", division.slug, False)
            if division.organization_id != organization.id:
                raise CommandError(
                    f"Division '{division_slug}' belongs to another organization."
                )

        assembly_category = (
            Category.objects.filter(type="assembly").order_by("id").first()
            or Category.objects.create(type="assembly", display_name="public", display_order=0, infos={})
        )
        assembly = Assembly.objects.filter(slug=assembly_slug).first()
        if assembly is None:
            assembly = Assembly.objects.create(
                division=division,
                slug=assembly_slug,
                display_name="Youth ministry",
                category=assembly_category,
                infos={},
            )
            self.note("assembly", assembly.slug, True)
        else:
            self.note("assembly", assembly.slug, False)

        character = Character.objects.filter(slug=character_slug).first()
        if character is None:
            character = Character.objects.create(
                assembly=assembly,
                slug=character_slug,
                display_name="Student",
                type="normal",
                infos={},
            )
            self.note("character", character.slug, True)
        else:
            self.note("character", character.slug, False)

        meet = Meet.objects.filter(slug=meet_slug).first()
        if meet is None:
            now = timezone.now()
            meet = Meet.objects.create(
                assembly=assembly,
                major_character=character,
                slug=meet_slug,
                display_name="Tally gathering",
                start=now,
                finish=now + timedelta(days=365 * 50),
                shown_audience=True,
                audience_editable=False,
                infos={
                    **Utility.meet_infos(),
                    "default_time_zone": organization.infos.get(
                        "default_time_zone", "America/Los_Angeles"
                    ),
                },
                site_type=ContentType.objects.get_for_model(Organization),
                site_id=str(organization.id),
            )
            self.note("meet", meet.slug, True)
        else:
            self.note("meet", meet.slug, False)

        user, user_created = User.objects.get_or_create(
            username=options["username"],
            defaults={"organization": organization, "is_active": True},
        )
        if user_created:
            user.set_unusable_password()
            user.save()
        elif user.organization_id != organization.id:
            raise CommandError(f"User '{user.username}' belongs to another organization.")
        self.note("user", user.username, user_created)
        user.groups.add(group)

        # privileged_to_edit() walks user.attendee.under_same_org_with(...), so
        # the integration user needs an attendee of its own in this division.
        attendee = Attendee.objects.filter(user=user).first()
        if attendee is None:
            attendee = Attendee.objects.create(
                division=division,
                user=user,
                first_name="Tally",
                last_name="Integration",
                # Explicit: the model default is the enum member, whose str()
                # overflows the 11-char column on a direct create.
                gender="UNSPECIFIED",
                infos=Utility.attendee_infos(),
            )
            self.note("attendee", str(attendee.id), True)
        else:
            self.note("attendee", str(attendee.id), False)

        # The write-privilege switch this app already uses: group names listed
        # in Organization.infos. Editing other attendees' records requires
        # membership of a group named in groups_see_all_meets_attendees.
        infos = organization.infos or {}
        granted = False
        for key in ("groups_see_all_meets_attendees", "counselor"):
            names = infos.get(key, [])
            if group.name not in names:
                infos[key] = [*names, group.name]
                granted = True
        if granted:
            organization.infos = infos
            organization.save(update_fields=["infos"])
        # groups_see_all_meets_attendees is what privileged_to_edit() checks;
        # "counselor" is the app's own word for door-working staff with broad
        # reads — without it, all_relations hides everything but "driver".
        self.note("organization privilege", group.name, granted)

        token, token_created = Token.objects.get_or_create(user=user)
        self.note("DRF token", "(printed below)", token_created)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Copy these into Tally's configuration:"))
        self.stdout.write(f"  A32_API_BASE_URL=<this server's https root>")
        self.stdout.write(f"  A32_TOKEN={token.key}")
        self.stdout.write(f"  A32_DIVISION_ID={division.id}")
        self.stdout.write(f"  A32_MEET_SLUG={meet.slug}")
        self.stdout.write(f"  A32_CHARACTER_SLUG={character.slug}")
        self.stdout.write(f"  A32_ASSEMBLY_SLUG={assembly.slug}")

    def note(self, kind, name, created):
        verb = "created" if created else "found"
        self.stdout.write(f"{verb:>8} {kind}: {name}")
