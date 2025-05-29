import pytest
from datetime import datetime, timedelta, timezone
from django.contrib.contenttypes.models import ContentType
from attendees.occasions.models.meet import Meet
from attendees.occasions.models.assembly import Assembly
from attendees.occasions.models.character import Character
from attendees.whereabouts.models import Division, Organization
from attendees.persons.models import Category
from django.contrib.auth.models import Group

@pytest.mark.django_db
class TestMeet:
    def setup_method(self):
        self.group = Group.objects.create(name="Test Group")
        self.organization = Organization.objects.create(display_name="Test Organization")
        self.division = Division.objects.create(display_name="Test Division", slug="test-division", organization=self.organization, audience_auth_group=self.group)
        self.category = Category.objects.create(display_name="Test Category", type="test", display_order=1)
        self.assembly = Assembly.objects.create(
            display_name="Test Assembly",
            slug="test-assembly",
            division=self.division,
            category=self.category,
        )
        self.character = Character.objects.create(
            assembly=self.assembly,
            display_name="Test Character",
            display_order=1,
            slug="test-assembly-test-character",
            type="normal",
        )
        self.site_type = ContentType.objects.get_for_model(Assembly)
        self.site_id = str(self.assembly.id)
        self.start = datetime.now(timezone.utc)
        self.finish = self.start + timedelta(hours=2)
        self.meet = Meet.objects.create(
            assembly=self.assembly,
            major_character=self.character,
            shown_audience=True,
            audience_editable=True,
            start=self.start,
            finish=self.finish,
            display_name="Test Meet",
            slug="test-meet",
            infos={"info": "Test info", "url": "https://example.com"},
            site_type=self.site_type,
            site_id=self.site_id,
        )

    def test_create_meet(self):
        assert self.meet.pk is not None
        assert self.meet.assembly == self.assembly
        assert self.meet.display_name == "Test Meet"
        assert self.meet.slug == "test-meet"
        assert self.meet.major_character == self.character
        assert self.meet.site_type == self.site_type
        assert self.meet.site_id == self.site_id
        assert self.meet.start == self.start
        assert self.meet.finish == self.finish
        assert self.meet.infos["info"] == "Test info"
        assert self.meet.infos["url"] == "https://example.com"

    def test_meet_str(self):
        s = str(self.meet)
        assert "Test Meet" in s
        assert "Test info" in s
        assert "https://example.com" in s

    def test_info_method(self):
        assert self.meet.info() == "Test info"

    def test_url_method(self):
        assert self.meet.url() == "https://example.com"

    def test_schedule_rules_empty(self):
        assert self.meet.schedule_rules == []

    def test_schedule_text_empty(self):
        assert self.meet.schedule_text() == ""
