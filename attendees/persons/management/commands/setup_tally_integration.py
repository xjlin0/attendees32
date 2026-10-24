"""
Provision everything the Tally check-in app needs to talk to this server.

Tally is a server-to-server client: it reads the roster over the JSON API with
a DRF token, creates quick-added visitors as attendees, keeps profile edits in
sync, files parents into families, and imports attendance history. This
command creates (or finds) the pieces that integration stands on,
idempotently — run it again and it changes nothing that already exists, so it
doubles as the way to look the values up.

    python manage.py setup_tally_integration --organization-slug cfcch

Tally files nobody into a meet. The only meets it touches are the ones it
reads history from, and reading a meet takes the group's name in that meet's
allowed groups: ``--readable-meet <slug>`` grants that on an existing meet, as
many times as needed. Nothing else about meets is created or changed.

Tally's people are filed under a division of Tally's own, ``<org>_tally``,
made if absent, so nothing has to be chosen and what came in from Tally is
easy to tell apart and triage; ``--division-slug`` names an existing division
instead.

It prints, at the end, exactly the values to copy into Tally's configuration
plus the token — DRF stores it retrievably, so later runs print it again by
design (it is the *server's* secret store, unlike hashed passwords).
"""
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from rest_framework.authtoken.models import Token

from attendees.occasions.models import Meet
from attendees.persons.models import Attendee, Category, Relation, Utility
from attendees.users.models import User
from attendees.whereabouts.models import Division, Organization

# Where the integration remembers what it was set up with: on its own attendee,
# which lives and dies with the church's data. The lifecycle commands read it.
PROVENANCE_KEY = "tally"


class Command(BaseCommand):
    help = "Provision the Tally integration: division, integration user, group, readable meets and DRF token."

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-slug",
            required=True,
            help="The organization Tally connects to. Must already exist.",
        )
        parser.add_argument(
            "--division-slug",
            default=None,
            help="An existing division to file Tally's people under. Default: <org-slug>_tally, made if absent.",
        )
        parser.add_argument("--username", default="tally-integration", help="The integration user.")
        parser.add_argument("--group", default="tally_integration", help="The auth group granted to the user.")
        parser.add_argument(
            "--readable-meet",
            action="append",
            default=[],
            metavar="SLUG",
            help="An existing meet Tally may read the history of. Repeatable.",
        )

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
        for category_id, name in ((Attendee.NON_FAMILY_CATEGORY, "non-family"), (Attendee.FAMILY_CATEGORY, "family")):
            if not Category.objects.filter(pk=category_id).exists():
                raise CommandError(
                    f"The {name} folk category is missing. Load the seed vocabulary first: "
                    "python manage.py loaddata fixtures/db_seed.json"
                )

        # Every meet named must exist in this organization before anything is
        # made, so a typo leaves the server exactly as it was.
        readable_meets = []
        for slug in options["readable_meet"]:
            meet = Meet.objects.filter(slug=slug, assembly__division__organization=organization).first()
            if meet is None:
                raise CommandError(f"No meet with slug '{slug}' in organization '{org_slug}'.")
            readable_meets.append(meet)

        group, group_created = Group.objects.get_or_create(name=options["group"])
        self.note("auth group", group.name, group_created)

        division_created = False
        if options["division_slug"]:
            division = Division.objects.filter(slug=options["division_slug"], organization=organization).first()
            if division is None:
                known = ", ".join(Division.objects.filter(organization=organization).values_list("slug", flat=True))
                raise CommandError(f"No division '{options['division_slug']}' in organization '{org_slug}'. Known: {known}")
        else:
            # Tally's own bucket, so what it pushed is easy to tell apart and
            # triage into the right division later.
            division = Division.objects.filter(slug=f"{org_slug}_tally", organization=organization).first()
            division_created = division is None
            if division_created:
                division = Division.objects.create(
                    organization=organization,
                    slug=f"{org_slug}_tally",
                    display_name="Tally",
                    audience_auth_group=group,
                    infos={},
                )
        self.note("division", division.slug, division_created)

        user, user_created = User.objects.get_or_create(
            username=options["username"],
            defaults={"organization": organization, "is_active": True},
        )
        if user_created:
            user.set_unusable_password()
            user.save()
        elif user.organization_id != organization.id:
            raise CommandError(f"User '{user.username}' belongs to another organization.")
        if not user.is_active:
            # A deleted integration, set up again: the same user comes back.
            user.is_active = True
            user.save(update_fields=["is_active"])
        self.note("user", user.username, user_created)
        user.groups.add(group)

        # privileged_to_edit() walks user.attendee.under_same_org_with(...), so
        # the integration user needs an attendee of its own in this division.
        attendee = Attendee.all_objects.filter(user=user).first()
        attendee_created = attendee is None
        if attendee_created:
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
        elif attendee.is_removed:
            attendee.is_removed = False
            attendee.save(update_fields=["is_removed"])
        self.note("attendee", str(attendee.id), attendee_created)

        # The write-privilege switch this app already uses: group names listed
        # in Organization.infos. Editing other attendees' records requires
        # membership of a group named in groups_see_all_meets_attendees;
        # "counselor" is the app's own word for door-working staff with broad
        # reads — without it, all_relations hides everything but "driver".
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
        self.note("organization privilege", group.name, granted)

        # organization_meets lists a meet only to callers whose group is in
        # its allowed_groups; that is what lets the history import see it.
        for meet in readable_meets:
            allowed_groups = meet.infos.get("allowed_groups") or []
            meet_granted = group.name not in allowed_groups
            if meet_granted:
                meet.infos = {**meet.infos, "allowed_groups": [*allowed_groups, group.name]}
                meet.save(update_fields=["infos"])
            self.note("readable meet", meet.slug, meet_granted)

        token, token_created = Token.objects.get_or_create(user=user)
        self.note("DRF token", "(printed below)", token_created)

        # What this run was given, kept where the data is, for backup and delete.
        previous = (attendee.infos or {}).get(PROVENANCE_KEY) or {}
        attendee.infos = {
            **(attendee.infos or {}),
            PROVENANCE_KEY: {
                "group": group.name,
                "division": division.slug,
                "division_created": previous.get("division_created", division_created),
                "readable_meets": sorted({*previous.get("readable_meets", []), *(m.slug for m in readable_meets)}),
            },
        }
        attendee.save(update_fields=["infos"])

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Copy these into Tally's configuration:"))
        self.stdout.write("  A32_API_BASE_URL=<this server's https root>")
        self.stdout.write(f"  A32_TOKEN={token.key}")
        self.stdout.write(f"  A32_DIVISION_ID={division.id}")

    def note(self, kind, name, created):
        verb = "created" if created else "found"
        self.stdout.write(f"{verb:>8} {kind}: {name}")
