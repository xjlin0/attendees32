import pytest
from datetime import datetime, timedelta, timezone
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from attendees.users.models import User
from attendees.whereabouts.models import Organization, Division
from attendees.persons.models import Attendee, Attending, AttendingMeet, Category, Utility, Relation
from attendees.persons.models.enum import GenderEnum
from attendees.occasions.models import Meet, Character, Assembly
from attendees.persons.services.atteningmeet_service import AttendingMeetService

@pytest.mark.django_db
class TestAttendingMeetService:
    def setup_method(self):
        self.relation = Relation.objects.create(id=0, title="test", gender=GenderEnum.UNSPECIFIED.value)
        self.organization = Organization.objects.create(display_name="Test Organization")
        self.group = Group.objects.create(name="Test Group")
        self.division = Division.objects.create(
            organization=self.organization,
            display_name="Test Division",
            slug="test-division",
            audience_auth_group=self.group
        )
        self.category = Category.objects.create(id=25, display_name="Test Category")
        self.category_1 = Category.objects.create(id=1, display_name="Scheduled")
        self.assembly = Assembly.objects.create(
            display_name="Test Assembly",
            slug="test-assembly",
            division=self.division,
            category=self.category,
        )
        self.character = Character.objects.create(
            assembly=self.assembly,
            display_name="Test Character",
            slug="test-character",
            type="normal",
        )
        self.site_type = ContentType.objects.get_for_model(Assembly)
        self.meet = Meet.objects.create(
            assembly=self.assembly,
            major_character=self.character,
            shown_audience=True,
            audience_editable=True,
            start=datetime.now(timezone.utc),
            finish=datetime.now(timezone.utc) + timedelta(days=1),
            display_name="Test Meet",
            slug="test-meet",
            site_type=self.site_type,
            site_id=str(self.assembly.id),
        )

        self.user = User.objects.create(
            username="testuser",
            email="testuser@example.com",
            organization=self.organization
        )

        self.attendee = Attendee.objects.create(
            first_name="John",
            last_name="Doe",
            division=self.division,
            user=self.user,
            gender="unspecified"
        )
        # Ensure user knows about attendee
        self.user.attendee = self.attendee
        self.user.save()

    def test_orderby_parser(self):
        orderbys = [
            {"selector": "category", "desc": False},
            {"selector": "attending__attendee", "desc": True},
            {"selector": "character", "desc": False},
            {"selector": "custom_field", "desc": True}
        ]
        result = AttendingMeetService.orderby_parser(orderbys)
        expected = [
            "category__display_name",
            "-attending__attendee__infos__names__original",
            "character__display_name",
            "-custom_field"
        ]
        assert result == expected

    def test_flip_attendingmeet_by_existing_attending_join(self):
        # We need to give the user permission to edit themselves
        self.organization.infos["groups_see_all_meets_attendees"] = [self.group.name]
        self.organization.save()
        self.user.groups.add(self.group)

        # Ensure there is already an auto-created attending
        assert Attending.objects.filter(attendee=self.attendee).count() == 1
        
        results = AttendingMeetService.flip_attendingmeet_by_existing_attending(
            current_user=self.user,
            attendees=[self.attendee],
            meet_id=self.meet.id,
            join=True
        )

        assert self.attendee in results
        attendingmeet = results[self.attendee]
        assert attendingmeet is not None
        assert attendingmeet.meet == self.meet
        assert attendingmeet.attending.attendee == self.attendee

    def test_flip_attendingmeet_by_existing_attending_leave(self):
        self.organization.infos["groups_see_all_meets_attendees"] = [self.group.name]
        self.organization.save()
        self.user.groups.add(self.group)

        # First join
        AttendingMeetService.flip_attendingmeet_by_existing_attending(
            current_user=self.user,
            attendees=[self.attendee],
            meet_id=self.meet.id,
            join=True
        )

        assert AttendingMeet.objects.filter(attending__attendee=self.attendee, meet=self.meet).count() == 1
        attendingmeet = AttendingMeet.objects.filter(attending__attendee=self.attendee, meet=self.meet).first()
        assert attendingmeet.finish > Utility.now_with_timezone()

        # Now leave
        AttendingMeetService.flip_attendingmeet_by_existing_attending(
            current_user=self.user,
            attendees=[self.attendee],
            meet_id=self.meet.id,
            join=False
        )

        attendingmeet.refresh_from_db()
        assert attendingmeet.finish <= Utility.now_with_timezone()

    def test_by_organization_meet_characters(self):
        self.organization.infos["groups_see_all_meets_attendees"] = [self.group.name]
        self.organization.save()
        self.user.groups.add(self.group)

        # Join the meet to have an AttendingMeet
        AttendingMeetService.flip_attendingmeet_by_existing_attending(
            current_user=self.user,
            attendees=[self.attendee],
            meet_id=self.meet.id,
            join=True
        )

        orderbys = [{"selector": "attending__attendee", "desc": False}]
        
        # Test basic retrieval
        qs = AttendingMeetService.by_organization_meet_characters(
            current_user=self.user,
            meet_slugs=[self.meet.slug],
            character_slugs=[self.character.slug],
            start=None,
            finish=None,
            orderbys=orderbys
        )

        assert qs.count() == 1
        assert qs.first().attending.attendee == self.attendee
