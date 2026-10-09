import pytest
from django.contrib.auth.models import Group

from attendees.persons.models import Attendee, Category, Folk, FolkAttendee, GenderEnum, Relation
from attendees.persons.serializers.folk_attendee_serializer import FolkAttendeeSerializer
from attendees.whereabouts.models import Division, Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def household():
    organization = Organization.objects.create(slug="serializer_org", display_name="Serializer org", infos={"settings": {}})
    division = Division.objects.create(
        organization=organization,
        slug="serializer_div",
        display_name="Division",
        audience_auth_group=Group.objects.create(name="serializer_group"),
        infos={},
    )
    category, _ = Category.objects.get_or_create(
        pk=Attendee.FAMILY_CATEGORY, defaults={"type": "folk", "display_name": "family", "infos": {}}
    )
    # Creating an attendee files it into a hidden non-family folk (relation pk 0).
    Category.objects.get_or_create(
        pk=Attendee.NON_FAMILY_CATEGORY, defaults={"type": "folk", "display_name": "other", "infos": {}}
    )
    Relation.objects.get_or_create(pk=Attendee.HIDDEN_ROLE, defaults={"title": "hidden", "gender": GenderEnum.UNSPECIFIED.value, "reciprocal_ids": []})
    role, _ = Relation.objects.get_or_create(title="child", defaults={"gender": GenderEnum.UNSPECIFIED.value, "reciprocal_ids": []})
    folk = Folk.objects.create(division=division, category=category, display_name="Doe family", infos={})
    attendee = Attendee.objects.create(division=division, first_name="Jane", last_name="Doe", gender=GenderEnum.UNSPECIFIED.value)
    return {"folk": folk, "attendee": attendee, "role": role}


class TestFolkAttendeeSerializer:
    def test_folk_is_written_by_id(self, household):
        serializer = FolkAttendeeSerializer(
            data={"folk": str(household["folk"].id), "attendee": str(household["attendee"].id), "role": household["role"].id, "infos": {}}
        )
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["folk"] == household["folk"]
        assert serializer.save().folk == household["folk"]

    def test_folk_is_read_back_nested(self, household):
        membership = FolkAttendee.objects.create(folk=household["folk"], attendee=household["attendee"], role=household["role"])
        data = FolkAttendeeSerializer(membership).data
        assert data["folk"]["id"] == str(household["folk"].id)
        assert data["folk"]["display_name"] == "Doe family"
        assert data["folk"]["category"] == Attendee.FAMILY_CATEGORY

    def test_an_unknown_folk_is_a_validation_error(self, household):
        serializer = FolkAttendeeSerializer(
            data={"folk": "00000000-0000-0000-0000-000000000000", "attendee": str(household["attendee"].id), "role": household["role"].id, "infos": {}}
        )
        assert not serializer.is_valid()
        assert "folk" in serializer.errors
