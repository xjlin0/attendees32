"""
Turn the golden :mod:`~attendees.tests.golden.roster` into database rows.

The builder is idempotent-by-construction rather than by upsert: it expects a
database that already carries ``fixtures/db_seed.json`` and no golden rows, and
it assigns every UUID primary key with :func:`uuid.uuid5` so two runs produce
byte-identical identifiers.  Integer primary keys for rows the seed does not
own (assemblies, meets, characters, teams the English youth ministry needs) are
hard-coded above the seed's range.

Signals are deliberately left switched on.  Half the point of the dataset is
that it exercises them:

* saving an :class:`~persons.models.Attendee` files them into a hidden
  non-family folk and opens an :class:`~persons.models.Attending`;
* saving a baptism :class:`~persons.models.Past` opens the AttendingMeet on the
  已受洗 meet (``past_category_to_attendingmeet_meet``);
* saving an AttendingMeet on the 已信主 meet writes the matching Past back
  (``automatic_creation.Past``);
* saving an AttendingMeet on the 通訊錄 meet flips ``Folk.infos.print_directory``
  (``automatic_modification.Folk``).

So the builder creates *one* side of each pair and lets the application produce
the other, which is exactly what the e2e tests then assert.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from allauth.account.models import EmailAddress
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from partial_date import PartialDate

from address.models import Address, Locality, State
from attendees.occasions.models import (
    Assembly,
    Attendance,
    Character,
    Gathering,
    Meet,
    Price,
    Team,
)
from attendees.persons.models import (
    Attendee,
    Attending,
    AttendingMeet,
    Category,
    Folk,
    FolkAttendee,
    Note,
    Past,
    Registration,
    Relation,
    Utility,
)
from attendees.users.models import User
from attendees.whereabouts.models import Division, Organization, Place, Room

from . import roster as roster_module
from .constants import (
    AttendanceCategory,
    AssemblySlugs,
    CHINESE_FELLOWSHIP_MEET_SLUGS,
    Characters,
    DIVISION_CROSSING,
    EducationCategory,
    FolkCategory,
    GOLDEN_UUID_NAMESPACE,
    Groups,
    HISTORY_WEEKS,
    MeetSlugs,
    NoteCategory,
    ORGANIZATION_ID,
    ROCK_SMALL_GROUP_CHARACTER_BY_GRADE,
    ROCK_TEAM_SLUG_BY_GRADE,
    StatusCategory,
    TeamSlugs,
)
from .roster import CHILD, CHINESE_ADULT, ENGLISH_ADULT, YOUTH, grade_index

NAMESPACE = uuid.UUID(GOLDEN_UUID_NAMESPACE)


def golden_uuid(kind: str, key: str) -> uuid.UUID:
    """A stable UUID for ``kind``/``key`` — same input, same primary key."""
    return uuid.uuid5(NAMESPACE, f"{kind}:{key}")


# ------------------------------------------------------------- golden vocabulary
#
# Primary keys above the seed's range, so a seed that grows never collides.
YOUTH_ASSEMBLY_ID = 20
GOLDEN_CHARACTER_IDS = {
    "youth_student": 100,
    "youth_sg_leader": 101,
    "youth_worship": 102,
    "crossing_worship_leader": 103,
    "crossing_worship_musician": 104,
    "crossing_worship_av": 105,
    "sunday_school_student": 106,
    "sunday_school_teacher": 107,
}
GOLDEN_MEET_IDS = {
    "youth_group": 100,
    "youth_sunday_school": 101,
    "crossing_worship_team": 102,
}
GOLDEN_TEAM_IDS = {
    "youth_middle_school": 100,
    "youth_high_school": 101,
    "youth_band": 102,
    "crossing_vocals": 103,
    "crossing_band": 104,
    "crossing_av": 105,
}

GOLDEN_MEET_SLUGS = {
    "youth_group": "d7c8Fd_cfcch_crossing_youth_group",
    "youth_sunday_school": "d7c8Fd_cfcch_crossing_youth_sunday_school",
    "crossing_worship_team": "d7c8Fd_cfcch_crossing_worship_team_practice",
}

FELLOWSHIP_TAG_TO_MEET_SLUG = dict(
    zip(roster_module.FELLOWSHIP_TAGS, CHINESE_FELLOWSHIP_MEET_SLUGS)
)

CHOIR_TEAM_BY_GENDER = {
    ("FEMALE", 0): TeamSlugs.CHOIR_SOPRANO,
    ("FEMALE", 1): TeamSlugs.CHOIR_ALTO,
    ("MALE", 0): TeamSlugs.CHOIR_TENOR,
    ("MALE", 1): TeamSlugs.CHOIR_BASS,
}

AFTER_SCHOOL_TEAMS = (
    TeamSlugs.AFTER_SCHOOL_TABLE_1,
    TeamSlugs.AFTER_SCHOOL_TABLE_2,
    TeamSlugs.AFTER_SCHOOL_TABLE_3,
)


# -------------------------------------------------------------------- personas
@dataclass(frozen=True)
class Persona:
    """A login the e2e suite drives the application with."""

    username: str
    groups: tuple
    attendee_key: Optional[str]
    is_superuser: bool = False
    organization_id: Optional[int] = ORGANIZATION_ID
    description: str = ""


PERSONAS = (
    Persona("golden_superuser", (), None, is_superuser=True,
            description="Django superuser, sees everything"),
    Persona("golden_data_organizer", (Groups.DATA_ORGANIZER, Groups.PARTICIPANT),
            "zhang_zhongxin",
            description="data admin: the pastor who maintains the roster"),
    Persona("golden_counselor", (Groups.DATA_COUNSELOR, Groups.PARTICIPANT),
            "xu_jianguo",
            description="counselor: privileged, sees counseling notes"),
    Persona("golden_children_organizer",
            (Groups.CHILDREN_ORGANIZER, Groups.PARTICIPANT), "lee_jonathan",
            description="Junior Ministry organizer"),
    Persona("golden_children_coworker",
            (Groups.CHILDREN_COWORKER, Groups.PARTICIPANT), "lee_joanna",
            description="Junior Ministry coworker"),
    Persona("golden_conference_organizer",
            (Groups.CONFERENCE_ORGANIZER, Groups.PARTICIPANT), "ma_liyun",
            description="summer retreat organizer"),
    Persona("golden_member", (Groups.PARTICIPANT,), "chen_zhiming",
            description="ordinary member and parent of two"),
    Persona("golden_crossing_member", (Groups.PARTICIPANT,), "wong_wilson",
            description="ordinary English-congregation member"),
    Persona("golden_youth", (Groups.PARTICIPANT,), "chen_grace",
            description="a 15-year-old with her own login"),
    Persona("golden_unaffiliated", (Groups.UNSPECIFIED,), None,
            description="a login with no attendee attached"),
    Persona("golden_outsider", (Groups.PARTICIPANT,), None, organization_id=None,
            description="authenticated but outside the organization"),
)

PERSONA_PASSWORD = "golden-password-1"

#: Who a confidential note is addressed to.  ``infos["show_secret"]`` is keyed
#: by attendee id, so a "counseling" note names the counselor persona's own
#: attendee and nobody else can read it — including the data admin.
SECRET_READER_BY_ROLE = {
    "counselor": "xu_jianguo",  # golden_counselor
    "coworker": "lee_jonathan",  # golden_children_organizer
}


# ---------------------------------------------------------------------- result
@dataclass
class GoldenDataset:
    """Handles onto everything the builder made, for tests to assert against."""

    roster: roster_module.Roster
    attendees: Dict[str, Attendee] = field(default_factory=dict)
    folks: Dict[str, Folk] = field(default_factory=dict)
    users: Dict[str, User] = field(default_factory=dict)
    meets: Dict[str, Meet] = field(default_factory=dict)
    characters: Dict[str, Character] = field(default_factory=dict)
    teams: Dict[str, Team] = field(default_factory=dict)
    gatherings: List[Gathering] = field(default_factory=list)
    registrations: Dict[str, Registration] = field(default_factory=dict)
    counts: Dict[str, int] = field(default_factory=dict)

    def attendee(self, key: str) -> Attendee:
        return self.attendees[key]

    def folk(self, key: str) -> Folk:
        return self.folks[key]

    def user(self, username: str) -> User:
        return self.users[username]


# --------------------------------------------------------------------- helpers
def _today() -> date:
    return date.today()


def _years_ago(years: float) -> date:
    return _today() - timedelta(days=int(round(365.2425 * years)))


def _dt(day: date, hour: int = 10, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=timezone.utc)


def _birthday(spec: roster_module.PersonSpec):
    """``(actual_birthday, estimated_birthday)`` for a person spec."""
    if spec.birthday_kind == "none" or spec.age is None and spec.birthday_kind != "unknown":
        if spec.birthday_kind == "unknown":
            return None, PartialDate("1800")
        return None, None
    if spec.birthday_kind == "unknown":
        # The codebase's placeholder for "nobody knows".
        return None, PartialDate("1800")
    born = _years_ago(spec.age + 0.3)
    if spec.birthday_kind == "year":
        return None, PartialDate(str(born.year))
    if spec.birthday_kind == "year_month":
        return None, PartialDate(f"{born.year}-{born.month:02d}")
    return born, None


def _contacts(spec: roster_module.PersonSpec, index: int) -> dict:
    contacts = {}
    if spec.phone_count >= 1:
        contacts["phone1"] = f"+1510{5550000 + index:07d}"
    if spec.phone_count >= 2:
        contacts["phone2"] = f"+1650{5550000 + index:07d}"
    if spec.email_count >= 1:
        contacts["email1"] = f"{spec.key}@example.org"
    if spec.email_count >= 2:
        contacts["email2"] = f"{spec.key}.alt@example.net"
    return contacts


def _fixed(spec: roster_module.PersonSpec) -> dict:
    fixed = {"mobility": spec.mobility}
    if spec.school_grade is not None:
        fixed["grade"] = grade_index(spec.school_grade)
        fixed["school_grade"] = spec.school_grade
    if spec.food_pref:
        fixed["food_pref"] = spec.food_pref
    if spec.nick_name:
        fixed["nick_name"] = spec.nick_name
    if spec.medical:
        fixed["medical"] = spec.medical
    if spec.insurer:
        fixed["insurer"] = spec.insurer
    return fixed


STATUS_TAG_TO_CATEGORY = {
    "baptized": StatusCategory.BAPTIZED,
    "member": StatusCategory.MEMBER,
    "visitor": StatusCategory.VISITOR,
    "catechumen": StatusCategory.CATECHUMEN,
    "interested": StatusCategory.INTERESTED,
    "disbeliever": StatusCategory.DISBELIEVER,
    "coworker": StatusCategory.COWORKER,
    "deacon": StatusCategory.DEACON,
}

EDUCATION_TAG_TO_CATEGORY = {
    "education_primary": EducationCategory.PRIMARY,
    "education_secondary": EducationCategory.SECONDARY,
    "education_college": EducationCategory.COLLEGE,
    "education_postgraduate": EducationCategory.POSTGRADUATE,
    "education_alternative": EducationCategory.ALTERNATIVE,
}


class GoldenBuilder:
    """Writes the roster into the database, section by section."""

    def __init__(self, roster: Optional[roster_module.Roster] = None):
        self.roster = roster or roster_module.build_roster()
        self.data = GoldenDataset(roster=self.roster)
        self.organization = Organization.objects.get(pk=ORGANIZATION_ID)
        self.divisions = {d.pk: d for d in Division.objects.filter(
            organization=self.organization)}
        self.attendee_ct = ContentType.objects.get_for_model(Attendee)
        self.folk_ct = ContentType.objects.get_for_model(Folk)
        self.room_ct = ContentType.objects.get_for_model(Room)
        self._relations = {r.pk: r for r in Relation.objects.all()}
        self._categories = {c.pk: c for c in Category.objects.all()}
        self._attendings: Dict[str, Attending] = {}

    # -- entry point ------------------------------------------------------
    def run(self) -> GoldenDataset:
        self.build_vocabulary()
        self.build_attendees()
        self.build_folks()
        self.build_contacts_and_schedulers()
        self.build_places()
        self.build_pasts_and_notes()
        self.build_participations()
        self.build_retreat()
        self.build_history()
        self.build_users()
        self.summarise()
        return self.data

    # -- 1. vocabulary the seed does not carry ----------------------------
    def build_vocabulary(self):
        """The English youth ministry, an English worship team, Sunday school roles."""
        crossing = self.divisions[DIVISION_CROSSING]
        youth_assembly, _ = Assembly.objects.update_or_create(
            pk=YOUTH_ASSEMBLY_ID,
            defaults={
                "display_name": "The Crossing Youth 青少年",
                "slug": AssemblySlugs.CROSSING_YOUTH,
                "division": crossing,
                "display_order": 1,
                "infos": {"fixed": {}, "contacts": {}, "need_age": 11},
            },
        )
        crossing_worship = Assembly.objects.get(slug=AssemblySlugs.CROSSING_WORSHIP_TEAM)
        chinese_sunday_school = Assembly.objects.get(
            slug=AssemblySlugs.CHINESE_SUNDAY_SCHOOL
        )

        character_specs = (
            ("youth_student", youth_assembly, "Youth Student 青少年學員", "audience"),
            ("youth_sg_leader", youth_assembly, "Youth Small Group Leader", "coworker"),
            ("youth_worship", youth_assembly, "Youth Worship Team", "coworker"),
            ("crossing_worship_leader", crossing_worship, "Worship Leader", "coworker"),
            ("crossing_worship_musician", crossing_worship, "Musician", "coworker"),
            ("crossing_worship_av", crossing_worship, "A/V Control", "coworker"),
            ("sunday_school_student", chinese_sunday_school, "主日學學員 student",
             "audience"),
            ("sunday_school_teacher", chinese_sunday_school, "主日學老師 teacher",
             "coworker"),
        )
        for key, assembly, display_name, type_ in character_specs:
            character, _ = Character.objects.update_or_create(
                pk=GOLDEN_CHARACTER_IDS[key],
                defaults={
                    "assembly": assembly,
                    "display_name": display_name,
                    "slug": f"golden_{key}",
                    "type": type_,
                    "display_order": GOLDEN_CHARACTER_IDS[key],
                    "infos": {},
                },
            )
            self.data.characters[key] = character

        room = Room.objects.get(slug="cfcch_fellowship_f205")
        worship_hall = Room.objects.get(slug="cfcch_worship_hall")
        meet_specs = (
            ("youth_group", youth_assembly, "Youth Group 青少團契 (Friday)", room,
             self.data.characters["youth_student"], True, True),
            ("youth_sunday_school", youth_assembly,
             "Youth Sunday School 青少主日學", room,
             self.data.characters["youth_student"], True, True),
            ("crossing_worship_team", crossing_worship,
             "The Crossing Worship Team", worship_hall,
             self.data.characters["crossing_worship_musician"], True, False),
        )
        for key, assembly, display_name, site, major_character, shown, editable in meet_specs:
            meet, _ = Meet.objects.update_or_create(
                pk=GOLDEN_MEET_IDS[key],
                defaults={
                    "assembly": assembly,
                    "display_name": display_name,
                    "slug": GOLDEN_MEET_SLUGS[key],
                    "major_character": major_character,
                    "shown_audience": shown,
                    "audience_editable": editable,
                    "start": _dt(_years_ago(3.0)),
                    "finish": _dt(_today() + timedelta(days=365 * 3)),
                    "site_type": self.room_ct,
                    "site_id": str(site.pk),
                    "infos": {
                        "allowed_models": ["gathering", "attendingmeet", "attendance",
                                           "eventrelation"],
                        "allowed_groups": [
                            Groups.PARTICIPANT, Groups.DATA_ORGANIZER,
                            Groups.DATA_COUNSELOR, Groups.CHILDREN_ORGANIZER,
                            Groups.CONFERENCE_ORGANIZER,
                        ],
                        "default_attendingmeet_in_weeks": 53,
                        "automatic_creation": {"Past": None, "Gathering": True,
                                               "Attendance": True},
                        "default_time_zone": "America/Los_Angeles",
                        "gathering_infos": {"generate_attendance": True},
                        "attendance": {},
                    },
                },
            )
            self.data.meets[key] = meet

        team_specs = (
            ("youth_middle_school", "youth_group", "Middle School 6-8"),
            ("youth_high_school", "youth_group", "High School 9-12"),
            ("youth_band", "youth_group", "Youth Band"),
            ("crossing_vocals", "crossing_worship_team", "Vocals"),
            ("crossing_band", "crossing_worship_team", "Band"),
            ("crossing_av", "crossing_worship_team", "A/V"),
        )
        for key, meet_key, display_name in team_specs:
            team, _ = Team.objects.update_or_create(
                pk=GOLDEN_TEAM_IDS[key],
                defaults={
                    "meet": self.data.meets[meet_key],
                    "display_name": display_name,
                    "slug": f"golden_{key}",
                    "display_order": GOLDEN_TEAM_IDS[key],
                    "site_type": self.room_ct,
                    "site_id": str(room.pk),
                    "infos": {},
                },
            )
            self.data.teams[key] = team

        # Seed meets, indexed by the short names the rest of the builder uses.
        for attribute in dir(MeetSlugs):
            if attribute.startswith("_"):
                continue
            slug = getattr(MeetSlugs, attribute)
            meet = Meet.objects.filter(slug=slug).first()
            if meet:
                self.data.meets[attribute.lower()] = meet
        for tag, slug in FELLOWSHIP_TAG_TO_MEET_SLUG.items():
            meet = Meet.objects.filter(slug=slug).first()
            if meet:
                self.data.meets[tag] = meet
        for slug in (
            TeamSlugs.CHOIR_SOPRANO, TeamSlugs.CHOIR_ALTO, TeamSlugs.CHOIR_TENOR,
            TeamSlugs.CHOIR_BASS, TeamSlugs.UNDER_THREE, TeamSlugs.ROCK_LARGE_GROUP,
            *ROCK_TEAM_SLUG_BY_GRADE.values(), *AFTER_SCHOOL_TEAMS,
        ):
            team = Team.objects.filter(slug=slug).first()
            if team:
                self.data.teams[slug] = team

    # -- 2. the people ----------------------------------------------------
    def build_attendees(self):
        for index, spec in enumerate(self.roster.people.values()):
            actual_birthday, estimated_birthday = _birthday(spec)
            attendee = Attendee(
                id=golden_uuid("attendee", spec.key),
                division=self.divisions[spec.division],
                first_name=spec.first_name,
                last_name=spec.last_name,
                first_name2=spec.first_name2 or None,
                last_name2=spec.last_name2 or None,
                gender=spec.gender,
                actual_birthday=actual_birthday,
                estimated_birthday=estimated_birthday,
                deathday=(
                    _years_ago(spec.died_years_ago) if spec.died_years_ago else None
                ),
                infos={
                    **Utility.attendee_infos(),
                    "fixed": _fixed(spec),
                    "contacts": _contacts(spec, index),
                },
                is_removed=spec.is_removed,
            )
            attendee.save()
            self.data.attendees[spec.key] = attendee
            # The post-save signal opened an Attending; hold onto it.
            self._attendings[spec.key] = attendee.attendings.first()

    # -- 3. families, carpools and other groupings ------------------------
    def build_folks(self):
        for folk_spec in self.roster.folks:
            folk = Folk(
                id=golden_uuid("folk", folk_spec.key),
                division=self.divisions[folk_spec.division],
                category=self._categories[folk_spec.category],
                display_name=folk_spec.display_name,
                display_order=folk_spec.display_order,
                infos={
                    "print_directory": folk_spec.print_directory,
                    "note": folk_spec.note,
                    "golden_key": folk_spec.key,
                },
                is_removed=folk_spec.is_removed,
            )
            folk.save()
            self.data.folks[folk_spec.key] = folk

            for member in folk_spec.members:
                attendee = self.data.attendees[member.person_key]
                show_secret = {
                    str(self.data.attendees[key].id): True
                    for key in member.show_secret_to
                }
                FolkAttendee.objects.create(
                    folk=folk,
                    attendee=attendee,
                    role=self._relations[member.role],
                    display_order=member.display_order,
                    start=(
                        _years_ago(member.start_years_ago)
                        if member.start_years_ago is not None
                        else None
                    ),
                    finish=(
                        _years_ago(member.finish_years_ago)
                        if member.finish_years_ago is not None
                        else None
                    ),
                    infos={
                        **Utility.relationship_infos(),
                        "show_secret": show_secret,
                        "comment": folk_spec.note or None,
                    },
                    is_removed=folk_spec.is_removed,
                )

    # -- 4. emergency contacts and schedulers -----------------------------
    def build_contacts_and_schedulers(self):
        for person_key, contact_keys in self.roster.emergency_contacts.items():
            attendee = self.data.attendees[person_key]
            attendee.infos["emergency_contacts"] = {
                str(self.data.attendees[key].id): True for key in contact_keys
            }
            attendee.save()
        for person_key, scheduler_keys in self.roster.schedulers.items():
            attendee = self.data.attendees[person_key]
            attendee.infos["schedulers"] = {
                str(self.data.attendees[key].id): True for key in scheduler_keys
            }
            attendee.save()

    # -- 5. addresses -----------------------------------------------------
    def build_places(self):
        california = State.objects.get(code="CA", country__code="US")
        localities: Dict[str, Locality] = {}
        for folk_spec in self.roster.folks:
            if not folk_spec.address:
                continue
            number, route, city, postal = folk_spec.address
            locality = localities.get(f"{city}-{postal}")
            if locality is None:
                locality, _ = Locality.objects.get_or_create(
                    name=city, postal_code=postal, state=california
                )
                localities[f"{city}-{postal}"] = locality
            raw = f"{number} {route}, {city}, CA {postal}"
            address, _ = Address.objects.get_or_create(
                raw=raw,
                defaults={
                    "street_number": number,
                    "route": route,
                    "locality": locality,
                    "formatted": raw,
                },
            )
            Place.objects.create(
                id=golden_uuid("place", folk_spec.key),
                content_type=self.folk_ct,
                object_id=str(self.data.folks[folk_spec.key].id),
                organization=self.organization,
                address=address,
                display_name="main",
                infos={"fixed": {}, "contacts": {}},
            )

        # A handful of attendees keep a second, personal address — a college
        # dorm and two people who moved out mid-year.
        personal = (
            ("zhang_esther", "1 Shields Avenue", "Davis", "95616", "resident"),
            ("tang_enci", "25000 Carlos Bee Boulevard", "Hayward", "94542", "resident"),
            ("song_wenbin", "3000 Mission Boulevard", "Hayward", "94544", "mailing"),
        )
        for key, route, city, postal, label in personal:
            locality, _ = Locality.objects.get_or_create(
                name=city, postal_code=postal, state=california
            )
            raw = f"{route}, {city}, CA {postal}"
            address, _ = Address.objects.get_or_create(
                raw=raw,
                defaults={"route": route, "locality": locality, "formatted": raw},
            )
            Place.objects.create(
                id=golden_uuid("place-personal", key),
                content_type=self.attendee_ct,
                object_id=str(self.data.attendees[key].id),
                organization=self.organization,
                address=address,
                display_name=label,
                display_order=1,
                start=_years_ago(1.5),
                infos={"fixed": {}, "contacts": {}},
            )

    # -- 6. statuses, education, notes ------------------------------------
    def build_pasts_and_notes(self):
        for index, spec in enumerate(self.roster.people.values()):
            attendee = self.data.attendees[spec.key]
            if spec.is_removed:
                continue

            # Baptism and membership are recorded as Pasts; the signal opens
            # the matching AttendingMeet on 已受洗 / 會員.
            if spec.has("baptized"):
                self._past(
                    attendee, StatusCategory.BAPTIZED,
                    when=self._baptism_when(spec, index),
                    display_name="受洗 baptised at CFCCH"
                    if index % 4 else "受洗 baptised in Taiwan",
                )
            for tag in ("member", "visitor", "catechumen", "interested",
                        "disbeliever", "coworker", "deacon"):
                if spec.has(tag):
                    self._past(
                        attendee, STATUS_TAG_TO_CATEGORY[tag],
                        when=self._status_when(spec, index, tag),
                        display_name=tag,
                    )

            for category_tag, years_ago, display_name in spec.pasts:
                category_id = EDUCATION_TAG_TO_CATEGORY.get(category_tag)
                if category_id is None:
                    continue
                self._past(
                    attendee, category_id,
                    when=PartialDate(str(_years_ago(years_ago).year)),
                    display_name=display_name,
                )

            for category_tag, body, secret_to in spec.notes:
                category_id = {
                    "public": NoteCategory.PUBLIC,
                    "coworker": NoteCategory.COWORKER,
                    "counseling": NoteCategory.COUNSELING,
                }[category_tag]
                infos = {**Utility.relationship_infos(), "body": body}
                # show_secret is keyed by the attendee id of the person allowed
                # to read it — that is what ApiCategorizedPastsViewSet filters
                # on — so point it at the persona who plays that role.
                confidant_key = SECRET_READER_BY_ROLE.get(secret_to)
                if confidant_key:
                    infos["show_secret"] = {
                        str(self.data.attendees[confidant_key].id): True
                    }
                # The attendee page's "note" tab reads Pasts whose category is
                # of type note, not the Note model — so write both, the way the
                # application itself does.
                Past.objects.create(
                    id=golden_uuid("past-note", f"{spec.key}:{category_tag}"),
                    content_type=self.attendee_ct,
                    object_id=str(attendee.id),
                    category=self._categories[category_id],
                    organization=self.organization,
                    when=PartialDate(_years_ago(0.5).isoformat()),
                    display_name=body[:50],
                    infos=infos,
                )
                Note.objects.create(
                    id=golden_uuid("note", f"{spec.key}:{category_tag}:{body[:16]}"),
                    content_type=self.attendee_ct,
                    object_id=str(attendee.id),
                    category=self._categories[category_id],
                    organization=self.organization,
                    body=body,
                    infos=infos,
                )

    def _baptism_when(self, spec, index):
        if spec.age is None:
            return PartialDate("1800")
        years_ago = max(0.5, min(spec.age - 12, 30) - (index % 7))
        if index % 11 == 0:
            return PartialDate(str(_years_ago(years_ago).year))  # year only
        if index % 13 == 0:
            born = _years_ago(years_ago)
            return PartialDate(f"{born.year}-{born.month:02d}")  # year and month
        return PartialDate(_years_ago(years_ago).isoformat())

    def _status_when(self, spec, index, tag):
        if tag in ("visitor", "interested"):
            return PartialDate(_years_ago(0.2 + (index % 5) * 0.1).isoformat())
        if spec.age is None:
            return PartialDate("1800")
        return PartialDate(_years_ago(max(0.3, min(spec.age - 14, 25) - index % 5)).isoformat())

    def _past(self, attendee, category_id, when, display_name):
        return Past.objects.create(
            id=golden_uuid("past", f"{attendee.id}:{category_id}"),
            content_type=self.attendee_ct,
            object_id=str(attendee.id),
            category=self._categories[category_id],
            organization=self.organization,
            when=when,
            display_name=display_name[:50],
            infos={**Utility.relationship_infos(), "comment": "golden dataset"},
        )

    # -- 7. participations -------------------------------------------------
    def build_participations(self):  # noqa: C901 - a long but flat mapping
        forever = Utility.forever()
        for index, spec in enumerate(self.roster.people.values()):
            if spec.is_removed or spec.has("deceased"):
                continue
            attending = self._attendings[spec.key]
            category_id = self._participation_category(spec)
            finish = (
                _dt(_years_ago(0.5)) if spec.has("inactive") else forever
            )

            # Sunday worship — the one participation everybody has.
            if spec.bucket == CHINESE_ADULT:
                self._attending_meet(
                    attending, "chinese_service", Characters.CONGREGATION,
                    category_id=category_id, finish=finish,
                )
            elif spec.bucket in (ENGLISH_ADULT, YOUTH):
                self._attending_meet(
                    attending, "english_service", Characters.CONGREGATION,
                    category_id=category_id, finish=finish,
                )
            else:
                self._attending_meet(
                    attending, "chinese_service", Characters.CONGREGATION,
                    category_id=category_id, finish=finish,
                )

            if spec.has("bilingual"):
                self._attending_meet(
                    attending, "english_service", Characters.CONGREGATION,
                    category_id=AttendanceCategory.SECONDARY, finish=forever,
                )

            # 通訊錄 — the signal flips Folk.infos.print_directory from here.
            if spec.has("directory"):
                self._attending_meet(
                    attending, "directory", Characters.IN_DIRECTORY,
                    category_id=AttendanceCategory.SCHEDULED, finish=forever,
                )

            # 已信主 — the signal writes the Past back from here.
            if spec.has("believer"):
                self._attending_meet(
                    attending, "believer", Characters.BELIEVER,
                    category_id=AttendanceCategory.ACTIVE, finish=forever,
                )
            if spec.has("visitor"):
                self._attending_meet(
                    attending, "visitor", Characters.VISITOR,
                    category_id=AttendanceCategory.ACTIVE, finish=forever,
                )

            if spec.has("choir"):
                team_slug = CHOIR_TEAM_BY_GENDER[(spec.gender, index % 2)]
                character = (
                    Characters.CHOIR_CONDUCTOR if index % 47 == 0
                    else Characters.CHOIR_ACCOMPANIST if index % 31 == 0
                    else Characters.CHOIR_SOLO if index % 23 == 0
                    else Characters.CHOIR_MEMBER
                )
                self._attending_meet(
                    attending, "chinese_choir", character, team_slug=team_slug,
                    category_id=AttendanceCategory.PRIMARY, finish=forever,
                )

            if spec.has("sunday_school"):
                self._attending_meet(
                    attending, "adult_sunday_school",
                    GOLDEN_CHARACTER_IDS["sunday_school_teacher"] if index % 9 == 0
                    else GOLDEN_CHARACTER_IDS["sunday_school_student"],
                    category_id=AttendanceCategory.ACTIVE, finish=forever,
                )

            for tag in roster_module.FELLOWSHIP_TAGS:
                if spec.has(tag):
                    character = (
                        Characters.CHINESE_FELLOWSHIP_LEADER if index % 17 == 0
                        else Characters.CHINESE_FELLOWSHIP_COWORKER if index % 11 == 0
                        else Characters.CHINESE_FELLOWSHIP_PARTICIPANT
                    )
                    self._attending_meet(
                        attending, tag, character,
                        category_id=category_id, finish=finish,
                    )

            if spec.has("library"):
                self._attending_meet(
                    attending, "library", Characters.LIBRARY_BORROWER,
                    category_id=AttendanceCategory.ACTIVE, finish=forever,
                    infos={"borrowed": index % 4},
                )

            # Children's programme.
            if spec.has("the_rock"):
                grade = max(0, min(spec.school_grade or 0, 5))
                self._attending_meet(
                    attending, "the_rock", Characters.JUNIOR_STUDENT,
                    team_slug=ROCK_TEAM_SLUG_BY_GRADE[grade],
                    category_id=category_id, finish=finish,
                    infos={"kid_points": (index % 7) * 5},
                )
            if spec.has("little_foot"):
                self._attending_meet(
                    attending, "little_foot", Characters.JUNIOR_STUDENT,
                    team_slug=TeamSlugs.UNDER_THREE,
                    category_id=category_id, finish=finish,
                )
            if spec.has("after_school"):
                self._attending_meet(
                    attending, "after_school_club", Characters.JUNIOR_STUDENT,
                    team_slug=AFTER_SCHOOL_TEAMS[index % 3],
                    category_id=category_id, finish=finish,
                )
            if spec.has("junior_coworker"):
                grade = 2 + (index % 4)
                self._attending_meet(
                    attending, "the_rock",
                    ROCK_SMALL_GROUP_CHARACTER_BY_GRADE[grade],
                    team_slug=ROCK_TEAM_SLUG_BY_GRADE[grade],
                    category_id=AttendanceCategory.PRIMARY, finish=forever,
                )
                self._attending_meet(
                    attending, "after_school_club",
                    Characters.AFTER_SCHOOL_COWORKER,
                    category_id=AttendanceCategory.SECONDARY, finish=forever,
                )

            # Youth ministry.
            if spec.has("youth_group"):
                grade = spec.school_grade or 6
                self._attending_meet(
                    attending, "youth_group",
                    GOLDEN_CHARACTER_IDS["youth_student"],
                    team_key="youth_middle_school" if grade <= 8 else "youth_high_school",
                    category_id=category_id, finish=finish,
                )
                self._attending_meet(
                    attending, "youth_sunday_school",
                    GOLDEN_CHARACTER_IDS["youth_student"],
                    category_id=category_id, finish=finish,
                )
            if spec.has("youth_worship"):
                self._attending_meet(
                    attending, "youth_group",
                    GOLDEN_CHARACTER_IDS["youth_worship"], team_key="youth_band",
                    category_id=AttendanceCategory.SECONDARY, finish=forever,
                )
            if spec.has("youth_leader"):
                self._attending_meet(
                    attending, "youth_group",
                    GOLDEN_CHARACTER_IDS["youth_sg_leader"],
                    team_key="youth_high_school",
                    category_id=AttendanceCategory.PRIMARY, finish=forever,
                )
            if spec.has("english_worship"):
                self._attending_meet(
                    attending, "crossing_worship_team",
                    GOLDEN_CHARACTER_IDS["crossing_worship_leader"] if index % 5 == 0
                    else GOLDEN_CHARACTER_IDS["crossing_worship_musician"],
                    team_key="crossing_vocals" if index % 2 else "crossing_band",
                    category_id=AttendanceCategory.PRIMARY, finish=forever,
                )

    def _participation_category(self, spec) -> int:
        if spec.has("inactive"):
            return AttendanceCategory.INACTIVE
        if spec.has("paused"):
            return AttendanceCategory.PAUSED
        if spec.has("remote"):
            return AttendanceCategory.REMOTE
        if spec.has("leave"):
            return AttendanceCategory.LEAVE
        return AttendanceCategory.SCHEDULED

    def _attending_meet(self, attending, meet_key, character_id, team_slug=None,
                        team_key=None, category_id=AttendanceCategory.SCHEDULED,
                        finish=None, start=None, infos=None):
        meet = self.data.meets.get(meet_key)
        if meet is None:
            return None
        team = None
        if team_key:
            team = self.data.teams.get(team_key)
        elif team_slug:
            team = self.data.teams.get(team_slug)
        return AttendingMeet.objects.create(
            attending=attending,
            meet=meet,
            character_id=character_id,
            team=team,
            category=self._categories[category_id],
            start=start or _dt(_years_ago(1.0)),
            finish=finish or Utility.forever(),
            infos=infos or {},
        )

    # -- 8. the summer retreat --------------------------------------------
    def build_retreat(self):
        assembly = Assembly.objects.get(slug=AssemblySlugs.SUMMER_RETREAT)
        prices = {}
        for name, price_type, value in (
            ("Adult, bed", "bed_regular", "195.00"),
            ("Adult, no bed", "no_bed_regular", "120.00"),
            ("Youth, bed", "bed_youth", "145.00"),
            ("Child under 5", "child_free", "0.00"),
        ):
            price, _ = Price.objects.update_or_create(
                assembly=assembly,
                display_name=name,
                defaults={
                    "price_type": price_type,
                    "price_value": Decimal(value),
                    "start": _dt(_years_ago(0.6)),
                    "finish": _dt(_today() + timedelta(days=120)),
                },
            )
            prices[price_type] = price

        registrants = [
            spec for spec in self.roster.people.values()
            if spec.has("retreat") and not spec.is_removed and not spec.has("deceased")
        ]
        registrants.sort(key=lambda spec: spec.key)

        # One registration per household head; family members ride on it.
        household_of = {}
        for folk_spec in self.roster.folks:
            if folk_spec.category != FolkCategory.FAMILY:
                continue
            for member in folk_spec.members:
                household_of.setdefault(member.person_key, folk_spec.key)

        registration_by_household = {}
        for index, spec in enumerate(registrants):
            household = household_of.get(spec.key, spec.key)
            registration = registration_by_household.get(household)
            if registration is None:
                registration = Registration.objects.create(
                    assembly=assembly,
                    registrant=self.data.attendees[spec.key],
                    infos={
                        "price": "195.00",
                        "donation": "25.00" if index % 4 == 0 else "0.00",
                        "credit": "35.50" if index % 9 == 0 else "0.00",
                        "apply_type": "online" if index % 3 else "paper",
                        "apply_key": f"{index + 1:04d}",
                    },
                )
                registration_by_household[household] = registration
                self.data.registrations[household] = registration

            if spec.bucket == CHILD:
                price = prices["child_free"]
                character = Characters.RETREAT_ATTENDEE
                program_meet = "retreat_junior_program"
            elif spec.bucket == YOUTH:
                price = prices["bed_youth"]
                character = Characters.RETREAT_ATTENDEE
                program_meet = "retreat_english_program"
            else:
                price = prices["bed_regular" if index % 5 else "no_bed_regular"]
                character = (
                    Characters.RETREAT_COWORKER if spec.has("coworker")
                    else Characters.RETREAT_ATTENDEE
                )
                program_meet = (
                    "retreat_chinese_program" if spec.bucket == CHINESE_ADULT
                    else "retreat_english_program"
                )

            attending = Attending.objects.create(
                attendee=self.data.attendees[spec.key],
                registration=registration,
                price=price,
                category="normal",
                infos={
                    "age": spec.age,
                    "bed_needs": 0 if price.price_type.startswith("no_bed") else 1,
                    "grade": grade_index(spec.school_grade)
                    if spec.school_grade is not None else None,
                    "mobility": spec.mobility * 100,
                },
            )
            self._attending_meet(
                attending, "retreat_accommodation", character,
                category_id=AttendanceCategory.CONFIRMED,
                finish=_dt(_today() + timedelta(days=120)),
            )
            self._attending_meet(
                attending, program_meet, character,
                category_id=AttendanceCategory.CONFIRMED,
                finish=_dt(_today() + timedelta(days=120)),
            )
            if index % 6 == 0:
                self._attending_meet(
                    attending, "retreat_panel",
                    Characters.RETREAT_PANEL_LEADER if index % 12 == 0
                    else Characters.RETREAT_PANEL_MEMBER,
                    team_slug="cfcch_2020_summer_retreat_chinese_panel1",
                    category_id=AttendanceCategory.CONFIRMED,
                    finish=_dt(_today() + timedelta(days=120)),
                )
            if index % 8 == 0:
                self._attending_meet(
                    attending, "retreat_transportation",
                    Characters.RETREAT_DRIVER if index % 16 == 0
                    else Characters.RETREAT_PASSENGER,
                    category_id=AttendanceCategory.CONFIRMED,
                    finish=_dt(_today() + timedelta(days=120)),
                )
            if index % 25 == 7:  # a few people cancelled after registering
                Attending.objects.filter(pk=attending.pk).update(category="not_going")

    # -- 9. eight weeks of Sunday history ----------------------------------
    def build_history(self):
        """Gatherings and attendances for the meets that meet every week."""
        weekly = (
            ("chinese_service", Characters.CONGREGATION, 10, 90),
            ("english_service", Characters.CONGREGATION, 12, 90),
            ("the_rock", Characters.JUNIOR_STUDENT, 10, 75),
            ("youth_group", GOLDEN_CHARACTER_IDS["youth_student"], 19, 120),
        )
        last_sunday = _today() - timedelta(days=(_today().weekday() + 1) % 7)

        attendances = []
        for meet_key, character_id, hour, minutes in weekly:
            meet = self.data.meets.get(meet_key)
            if meet is None:
                continue
            participants = list(
                AttendingMeet.objects.filter(
                    meet=meet, character_id=character_id, is_removed=False
                ).select_related("attending")
            )
            for week in range(HISTORY_WEEKS):
                day = last_sunday - timedelta(weeks=week)
                start = _dt(day, hour)
                gathering = Gathering.objects.create(
                    meet=meet,
                    start=start,
                    finish=start + timedelta(minutes=minutes),
                    display_name=f"{meet.display_name} {day.isoformat()}",
                    site_type=meet.site_type,
                    site_id=meet.site_id,
                    infos={"generate_attendance": True},
                )
                self.data.gatherings.append(gathering)
                for position, attending_meet in enumerate(participants):
                    if (position + week) % 9 == 4:
                        continue  # nobody attends every single week
                    if (position + week) % 13 == 0:
                        category_id = AttendanceCategory.ABSENT
                    elif (position + week) % 17 == 0:
                        category_id = AttendanceCategory.REMOTE
                    elif (position + week) % 23 == 0:
                        category_id = AttendanceCategory.LEAVE
                    else:
                        category_id = AttendanceCategory.ATTENDED
                    # The children's register of the most recent Sunday is
                    # left part-finished: some are still in the room, nobody
                    # having signed for them yet. That is what the roll-call
                    # screen actually looks like while it is being used, and
                    # a dataset where every child is already collected cannot
                    # show it.
                    still_here = (
                        meet_key == "the_rock"
                        and week == 0
                        and category_id == AttendanceCategory.ATTENDED
                        and position % 3 == 0
                    )
                    attendances.append(
                        Attendance(
                            gathering=gathering,
                            attending=attending_meet.attending,
                            character_id=character_id,
                            team=attending_meet.team,
                            category_id=category_id,
                            start=start,
                            finish=None if still_here else start + timedelta(minutes=minutes),
                            infos={"kid_points": position % 5}
                            if meet_key == "the_rock" else {},
                        )
                    )
        Attendance.objects.bulk_create(attendances, batch_size=500)

    # -- 10. logins ---------------------------------------------------------
    def build_users(self):
        groups = {group.name: group for group in Group.objects.all()}
        # Rebuilding on top of a previous run (load_golden_data --force) must
        # not trip over the usernames it left behind.
        User.objects.filter(
            username__in=[persona.username for persona in PERSONAS]
        ).delete()
        for persona in PERSONAS:
            user = User.objects.create_user(
                username=persona.username,
                email=f"{persona.username}@example.org",
                password=PERSONA_PASSWORD,
                name=persona.description,
                is_superuser=persona.is_superuser,
                is_staff=persona.is_superuser,
            )
            if persona.organization_id:
                user.organization = self.organization
            user.infos = {"settings": {"persona": persona.username}}
            user.save()
            for group_name in persona.groups:
                group = groups.get(group_name)
                if group:
                    user.groups.add(group)
            # ACCOUNT_EMAIL_VERIFICATION is mandatory, so a login without a
            # verified address is bounced to the "confirm your email" page —
            # every real account has one of these, and the browser tests sign
            # in through the real form.
            EmailAddress.objects.get_or_create(
                user=user,
                email=user.email,
                defaults={"verified": True, "primary": True},
            )
            if persona.attendee_key:
                attendee = self.data.attendees[persona.attendee_key]
                attendee.user = user
                attendee.save()
            self.data.users[persona.username] = user

    # -- 11. the manifest ---------------------------------------------------
    def summarise(self):
        organization_attendees = Attendee.objects.filter(
            division__organization=self.organization
        )
        self.data.counts = {
            "attendees": organization_attendees.count(),
            "attendees_including_removed": Attendee.all_objects.filter(
                division__organization=self.organization
            ).count(),
            "chinese_adults": len(self.roster.bucket(CHINESE_ADULT)),
            "english_adults": len(self.roster.bucket(ENGLISH_ADULT)),
            "youth": len(self.roster.bucket(YOUTH)),
            "children": len(self.roster.bucket(CHILD)),
            "families": Folk.objects.filter(
                category_id=FolkCategory.FAMILY,
                division__organization=self.organization,
            ).count(),
            "folk_attendees": FolkAttendee.objects.count(),
            "pasts": Past.objects.filter(organization=self.organization).count(),
            "notes": Note.objects.filter(organization=self.organization).count(),
            "attendings": Attending.objects.count(),
            "attending_meets": AttendingMeet.objects.count(),
            "registrations": Registration.objects.count(),
            "gatherings": len(self.data.gatherings),
            "attendances": Attendance.objects.count(),
            "places": Place.objects.filter(organization=self.organization).count(),
            "users": len(self.data.users),
        }


#: ``fixtures/db_seed.json`` links its nineteen demo attendees to two users by
#: natural key, so — exactly as the README's "create 2 superusers" step says —
#: they have to exist before the seed loads.
SEED_USERNAMES = ("hagar", "jack")


def purge_seed_people():
    """Drop the seed's nineteen demo people, keeping its vocabulary.

    ``fixtures/db_seed.json`` ships both a vocabulary (organizations, meets,
    characters, relations, menus) and a handful of sample attendees to
    illustrate it.  The golden dataset wants the first and replaces the second,
    so the congregation really is 350 people and a count is a count.
    """
    from schedule.models import Occurrence

    attendee_ct = ContentType.objects.get_for_model(Attendee)
    folk_ct = ContentType.objects.get_for_model(Folk)
    Attendance.all_objects.all().delete()
    # Gatherings too, so the eight weeks of history are exactly the ones this
    # builder wrote — and so a second run does not collide with the first on
    # (meet, site, start). The Gathering post-save signal mirrors each one into
    # a schedule Occurrence, which would otherwise be left orphaned.
    Occurrence.objects.filter(title__startswith="gathering#").delete()
    Gathering.all_objects.all().delete()
    AttendingMeet.all_objects.all().delete()
    Attending.all_objects.all().delete()
    Registration.all_objects.all().delete()
    Past.all_objects.filter(content_type=attendee_ct).delete()
    Note.all_objects.filter(content_type=attendee_ct).delete()
    Place.all_objects.filter(content_type__in=[attendee_ct, folk_ct]).delete()
    FolkAttendee.all_objects.all().delete()
    Folk.all_objects.all().delete()
    Attendee.all_objects.all().delete()


def create_seed_users():
    for username in SEED_USERNAMES:
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(
                username=username,
                email=f"{username}@example.org",
                password=PERSONA_PASSWORD,
            )


def build_golden_dataset(load_seed: bool = False) -> GoldenDataset:
    """Build the whole dataset, optionally loading ``fixtures/db_seed.json`` first."""
    if load_seed:
        create_seed_users()
        call_command("loaddata", "fixtures/db_seed.json", verbosity=0)
        # django_content_type carries two extra columns in this project
        # (genres, display_order); the site-picker API reads them by raw SQL
        # and they are populated by a management command, not a migration.
        call_command("update_content_types", verbosity=0)
    purge_seed_people()
    return GoldenBuilder().run()
