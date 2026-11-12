import pytest
from datetime import date
from django.contrib.auth.models import Group
from django.core.management import call_command

from attendees.persons.models import Attendee, Category, Relation
from attendees.persons.models.attendee import AttendeesHistory
from attendees.persons.models.enum import GenderEnum
from attendees.persons.services.attendee_service import AttendeeService
from attendees.persons.tasks import advance_grades
from attendees.whereabouts.models import Division, Organization


GRADE_CONVERTER_STANDARD = [
    "Under three 1",   # 0
    "Under three 2",   # 1
    "Under three 3",   # 2
    "Preschool 1",     # 3
    "Preschool 2",     # 4
    "Kindergarten 1",   # 5
    "Kindergarten 2",   # 6
    "G1",              # 7
    "G2",              # 8
    "G3",              # 9
    "G4",              # 10
    "G5",              # 11
    "G6",              # 12
    "G7",              # 13
    "G8",              # 14
    "G9",              # 15
    "G10",             # 16
    "G11",             # 17
    "G12",             # 18
    "Postsecondary 1", # 19
    "Postsecondary 2", # 20
]


@pytest.mark.django_db
class TestAdvanceGrades:
    def setup_method(self):
        Category.objects.get_or_create(
            id=Attendee.FAMILY_CATEGORY,
            defaults={"display_name": "Family", "type": "folk"},
        )
        Category.objects.get_or_create(
            id=Attendee.NON_FAMILY_CATEGORY,
            defaults={"display_name": "Other", "type": "folk"},
        )
        Relation.objects.get_or_create(
            id=Attendee.RELATION_DEFAULT if hasattr(Attendee, "RELATION_DEFAULT") else 0,
            defaults={"title": "default", "gender": GenderEnum.UNSPECIFIED.value},
        )
        self.auth_group = Group.objects.create(name="AdvanceGradesGroup")

        self.org_with_grades = Organization.objects.create(
            display_name="CFCCH Hayward",
            slug="cfcch-hayward",
            infos={"grade_converter": GRADE_CONVERTER_STANDARD},
        )
        self.div_with_grades = Division.objects.create(
            organization=self.org_with_grades,
            display_name="Children Ministry",
            slug="children-ministry",
            audience_auth_group=self.auth_group,
        )

        self.org_in_settings = Organization.objects.create(
            display_name="CFCCH Settings Org",
            slug="cfcch-settings-org",
            infos={"settings": {"grade_converter": GRADE_CONVERTER_STANDARD}},
        )
        self.div_in_settings = Division.objects.create(
            organization=self.org_in_settings,
            display_name="Settings Division",
            slug="settings-division",
            audience_auth_group=self.auth_group,
        )

        self.org_no_converter = Organization.objects.create(
            display_name="No Converter Church",
            slug="no-converter-church",
            infos={},
        )
        self.div_no_converter = Division.objects.create(
            organization=self.org_no_converter,
            display_name="No Converter Div",
            slug="no-converter-div",
            audience_auth_group=self.auth_group,
        )

        self.org_empty_converter = Organization.objects.create(
            display_name="Empty Converter Church",
            slug="empty-converter-church",
            infos={"grade_converter": []},
        )

    def test_get_g12_index(self):
        assert AttendeeService.get_g12_index(GRADE_CONVERTER_STANDARD) == 18
        assert AttendeeService.get_g12_index(["G1", "G2", "Grade 12", "Postsecondary"]) == 2
        assert AttendeeService.get_g12_index(["G1", "G2", "12th Grade"]) == 2
        assert AttendeeService.get_g12_index(["G1", "G2", "G3"]) is None
        assert AttendeeService.get_g12_index([]) is None
        assert AttendeeService.get_g12_index(None) is None

    def test_skips_organizations_without_grade_converter(self):
        attendee_no_conv = Attendee.objects.create(
            first_name="NoConv",
            last_name="Kid",
            division=self.div_no_converter,
            gender=GenderEnum.UNSPECIFIED.value,
            infos={"fixed": {"grade": 5}},
        )

        result = advance_grades(organization_slug=self.org_no_converter.slug)
        assert result["total_updated"] == 0
        assert result["organizations_skipped"] == 1
        assert result["organizations_processed"] == 0

        attendee_no_conv.refresh_from_db()
        assert attendee_no_conv.infos["fixed"]["grade"] == 5

    def test_skips_organizations_with_empty_converter(self):
        result = advance_grades(organization_slug=self.org_empty_converter.slug)
        assert result["total_updated"] == 0
        assert result["organizations_skipped"] == 1

    def test_advances_grades_regular_students(self):
        # Under three 1 (index 0)
        kid0 = Attendee.objects.create(
            first_name="Toddler",
            last_name="One",
            division=self.div_with_grades,
            gender=GenderEnum.UNSPECIFIED.value,
            infos={"fixed": {"grade": 0}},
        )
        # Kindergarten 2 (index 6) -> should become G1 (index 7)
        kid_k2 = Attendee.objects.create(
            first_name="Kinder",
            last_name="Two",
            division=self.div_with_grades,
            gender=GenderEnum.UNSPECIFIED.value,
            infos={"fixed": {"grade": 6}},
        )
        # G11 (index 17) -> should become G12 (index 18)
        kid_g11 = Attendee.objects.create(
            first_name="High",
            last_name="Junior",
            division=self.div_with_grades,
            gender=GenderEnum.UNSPECIFIED.value,
            infos={"fixed": {"grade": 17, "school_grade": 11, "food_pref": "nut-free"}},
        )

        result = advance_grades(organization_slug=self.org_with_grades.slug)

        assert result["total_updated"] == 3
        assert result["total_capped"] == 0

        kid0.refresh_from_db()
        kid_k2.refresh_from_db()
        kid_g11.refresh_from_db()

        assert kid0.infos["fixed"]["grade"] == 1
        assert kid_k2.infos["fixed"]["grade"] == 7
        assert kid_g11.infos["fixed"]["grade"] == 18
        assert kid_g11.infos["fixed"]["school_grade"] == 12
        assert kid_g11.infos["fixed"]["food_pref"] == "nut-free"

    def test_capped_at_g12(self):
        # G12 student (index 18)
        g12_student = Attendee.objects.create(
            first_name="Graduating",
            last_name="Senior",
            division=self.div_with_grades,
            gender=GenderEnum.UNSPECIFIED.value,
            infos={"fixed": {"grade": 18, "school_grade": 12}},
        )
        # Postsecondary student (index 19)
        college_student = Attendee.objects.create(
            first_name="College",
            last_name="Freshman",
            division=self.div_with_grades,
            gender=GenderEnum.UNSPECIFIED.value,
            infos={"fixed": {"grade": 19}},
        )

        result = advance_grades(organization_slug=self.org_with_grades.slug)

        assert result["total_updated"] == 0
        assert result["total_capped"] == 2

        g12_student.refresh_from_db()
        college_student.refresh_from_db()

        # Grade remains capped!
        assert g12_student.infos["fixed"]["grade"] == 18
        assert g12_student.infos["fixed"]["school_grade"] == 12
        assert college_student.infos["fixed"]["grade"] == 19

    def test_supports_grade_converter_in_settings(self):
        kid = Attendee.objects.create(
            first_name="Settings",
            last_name="Kid",
            division=self.div_in_settings,
            gender=GenderEnum.UNSPECIFIED.value,
            infos={"fixed": {"grade": 7}},  # G1
        )

        result = advance_grades(organization_slug=self.org_in_settings.slug)

        assert result["total_updated"] == 1
        kid.refresh_from_db()
        assert kid.infos["fixed"]["grade"] == 8  # G2

    def test_ignores_inactive_deceased_merged_or_ungraded(self):
        # Soft-deleted
        deleted_kid = Attendee.objects.create(
            first_name="Deleted",
            last_name="Kid",
            division=self.div_with_grades,
            gender=GenderEnum.UNSPECIFIED.value,
            is_removed=True,
            infos={"fixed": {"grade": 3}},
        )
        # Deceased
        deceased_kid = Attendee.objects.create(
            first_name="Deceased",
            last_name="Kid",
            division=self.div_with_grades,
            gender=GenderEnum.UNSPECIFIED.value,
            deathday=date(2025, 1, 1),
            infos={"fixed": {"grade": 3}},
        )
        # Merged into another
        target_attendee = Attendee.objects.create(
            first_name="Target",
            last_name="Kid",
            division=self.div_with_grades,
            gender=GenderEnum.UNSPECIFIED.value,
            infos={"fixed": {"grade": 3}},
        )
        merged_kid = Attendee.objects.create(
            first_name="Merged",
            last_name="Kid",
            division=self.div_with_grades,
            gender=GenderEnum.UNSPECIFIED.value,
            merged_into=target_attendee,
            infos={"fixed": {"grade": 3}},
        )
        # Adult without grade
        adult = Attendee.objects.create(
            first_name="Adult",
            last_name="Member",
            division=self.div_with_grades,
            gender=GenderEnum.UNSPECIFIED.value,
            infos={"fixed": {"mobility": 2}},
        )

        result = advance_grades(organization_slug=self.org_with_grades.slug)

        # Only target_attendee is active with grade
        assert result["total_updated"] == 1

        deleted_kid.refresh_from_db()
        deceased_kid.refresh_from_db()
        merged_kid.refresh_from_db()
        adult.refresh_from_db()
        target_attendee.refresh_from_db()

        assert deleted_kid.infos["fixed"]["grade"] == 3
        assert deceased_kid.infos["fixed"]["grade"] == 3
        assert merged_kid.infos["fixed"]["grade"] == 3
        assert "grade" not in adult.infos["fixed"]
        assert target_attendee.infos["fixed"]["grade"] == 4

    def test_dry_run_does_not_modify_database(self):
        kid = Attendee.objects.create(
            first_name="DryRun",
            last_name="Student",
            division=self.div_with_grades,
            gender=GenderEnum.UNSPECIFIED.value,
            infos={"fixed": {"grade": 10}},  # G4
        )

        result = advance_grades(organization_slug=self.org_with_grades.slug, dry_run=True)

        assert result["total_updated"] == 1
        kid.refresh_from_db()
        # Database value remains unchanged in dry-run mode!
        assert kid.infos["fixed"]["grade"] == 10

    def test_management_command_execution(self):
        kid = Attendee.objects.create(
            first_name="Cmd",
            last_name="Student",
            division=self.div_with_grades,
            gender=GenderEnum.UNSPECIFIED.value,
            infos={"fixed": {"grade": 8}},  # G2
        )

        # Dry run via command
        call_command("advance_grades", organization_slug=self.org_with_grades.slug, dry_run=True)
        kid.refresh_from_db()
        assert kid.infos["fixed"]["grade"] == 8

        # Real run via command
        call_command("advance_grades", organization_slug=self.org_with_grades.slug)
        kid.refresh_from_db()
        assert kid.infos["fixed"]["grade"] == 9  # G3

    def test_pghistory_context_recorded(self):
        kid = Attendee.objects.create(
            first_name="History",
            last_name="Test",
            division=self.div_with_grades,
            gender=GenderEnum.UNSPECIFIED.value,
            infos={"fixed": {"grade": 5}},
        )

        advance_grades(organization_slug=self.org_with_grades.slug)

        latest_history = (
            AttendeesHistory.objects.filter(pgh_obj_id=kid.id)
            .order_by("-pgh_id")
            .first()
        )
        assert latest_history is not None
        assert latest_history.pgh_context is not None
        assert "advance grades" in latest_history.pgh_context.metadata.get("modifier", "")

    def test_organization_infos_list_kwarg_support(self):
        kid = Attendee.objects.create(
            first_name="OrgList",
            last_name="Student",
            division=self.div_with_grades,
            gender=GenderEnum.UNSPECIFIED.value,
            infos={"fixed": {"grade": 1}},
        )

        result = advance_grades(organization_infos=[{"organization_slug": self.org_with_grades.slug}])
        assert result["total_updated"] == 1
        kid.refresh_from_db()
        assert kid.infos["fixed"]["grade"] == 2
