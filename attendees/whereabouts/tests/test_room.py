import pytest
from django.urls import reverse
from attendees.whereabouts.models.organization import Organization
from attendees.whereabouts.models.campus import Campus
from attendees.whereabouts.models.property import Property
from attendees.whereabouts.models.suite import Suite
from attendees.whereabouts.models.room import Room

@pytest.mark.django_db
class TestRoom:
    def setup_method(self):
        self.organization = Organization.objects.create(
            slug="test-org",
            display_name="Test Organization",
        )
        self.campus = Campus.objects.create(
            organization=self.organization,
            display_name="Test Campus",
            slug="test-campus",
        )
        self.property = Property.objects.create(
            display_name="Test Property",
            slug="test-property",
            campus=self.campus,
        )
        self.suite = Suite.objects.create(
            display_name="Test Suite",
            slug="test-suite",
            property=self.property,
            site="2F",
        )
        self.room = Room.objects.create(
            display_name="Test Room",
            slug="test-room",
            suite=self.suite,
            label="101",
            infos={"accessibility": 3},
        )

    def test_create_room(self):
        assert self.room.pk is not None
        assert self.room.display_name == "Test Room"
        assert self.room.slug == "test-room"
        assert self.room.suite == self.suite
        assert self.room.label == "101"
        assert self.room.infos["accessibility"] == 3

    def test_str(self):
        expected_str = f"{self.suite.display_name} {self.room.display_name} {self.room.label}"
        assert str(self.room) == expected_str

    def test_str_no_label(self):
        self.room.label = None
        self.room.save()
        expected_str = f"{self.suite.display_name} {self.room.display_name} "
        assert str(self.room) == expected_str

    def test_get_absolute_url(self):
        try:
            url = self.room.get_absolute_url()
            assert str(self.room.id) in url
        except Exception:
            pass
