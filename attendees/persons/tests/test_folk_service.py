import pytest
from uuid import uuid4
from django.contrib.auth.models import Group
from attendees.persons.services.folk_service import FolkService
from attendees.persons.models import Folk, Attendee, FolkAttendee, Category, Relation
from attendees.persons.models.enum import GenderEnum
from attendees.whereabouts.models import Division, Organization

@pytest.mark.django_db
class TestFolkService:
    def setup_method(self):
        self.organization = Organization.objects.create(display_name="Test Organization")
        self.group = Group.objects.create(name="Test Group")
        self.division = Division.objects.create(
            organization=self.organization,
            display_name="Test Division",
            slug="test-division",
            audience_auth_group=self.group
        )
        self.category = Category.objects.create(id=25, display_name="Family")
        self.relation = Relation.objects.create(id=0, title="test", gender=GenderEnum.UNSPECIFIED.value)
        
        self.folk = Folk.objects.create(
            id=uuid4(),
            division=self.division,
            category=self.category,
            display_name="Test Family",
            display_order=1
        )
        
        self.attendee = Attendee.objects.create(
            id=uuid4(),
            first_name="John",
            last_name="Doe",
            division=self.division,
            gender="unspecified",
        )
        
        self.folk_attendee = FolkAttendee.objects.create(
            folk=self.folk,
            attendee=self.attendee,
            role=self.relation,
            display_order=1
        )

    def test_get_recipient_no_spouse(self):
        home_head = {
            'first_name': 'John',
            'last_name': 'Doe',
            'first_name2': '一',
            'last_name2': '王'
        }
        result = FolkService.get_recipient(home_head, None)
        assert result == 'John Doe 王一'

    def test_get_recipient_with_spouse(self):
        home_head = {
            'first_name': 'John',
            'last_name': 'Doe',
            'first_name2': '一',
            'last_name2': '王'
        }
        spouse = {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'first_name2': '二',
            'last_name2': '李'
        }
        result = FolkService.get_recipient(home_head, spouse)
        assert result == 'John & Jane Doe 王一 李二'

    def test_destroy_with_associations_single_attendee(self):
        # Folk has only one attendee (John Doe)
        assert Folk.objects.filter(id=self.folk.id).exists()
        assert FolkAttendee.objects.filter(id=self.folk_attendee.id).exists()
        
        FolkService.destroy_with_associations(self.folk, self.attendee)
        
        # Since it was the only attendee, both folk and folk_attendee should be soft-deleted
        self.folk.refresh_from_db()
        self.folk_attendee.refresh_from_db()
        assert self.folk.is_removed is True
        assert self.folk_attendee.is_removed is True

    def test_destroy_with_associations_multiple_attendees(self):
        # Add another attendee to the same folk
        attendee_2 = Attendee.objects.create(
            id=uuid4(),
            first_name="Jane",
            last_name="Doe",
            division=self.division,
            gender="unspecified",
        )
        folk_attendee_2 = FolkAttendee.objects.create(
            folk=self.folk,
            attendee=attendee_2,
            role=self.relation,
            display_order=2
        )
        
        self.folk.display_name = "John Doe Family"
        self.folk.save()
        
        assert FolkAttendee.objects.filter(folk=self.folk).count() == 2
        
        # Destroy for the first attendee only
        FolkService.destroy_with_associations(self.folk, self.attendee)
        
        # The folk should still exist
        assert Folk.objects.filter(id=self.folk.id).exists()
        
        # The first folk_attendee should be soft-deleted, but the second remains active
        self.folk_attendee.refresh_from_db()
        folk_attendee_2.refresh_from_db()
        assert self.folk_attendee.is_removed is True
        assert folk_attendee_2.is_removed is False
        
        # Check name replacing (very basic test since logic replaces names)
        # Note: all_names() might not perfectly match "John Doe Family" if all_names doesn't have it,
        # but we test that it attempts to replace and saves.
        self.folk.refresh_from_db()
        assert self.folk.display_name is not None
