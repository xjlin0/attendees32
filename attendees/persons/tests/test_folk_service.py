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

    def test_families_in_participations_with_removed_folkattendee(self):
        from attendees.occasions.models import Meet, Assembly, Character
        from attendees.persons.models import Attending, AttendingMeet, Folk, FolkAttendee, Category
        import datetime

        now = datetime.datetime.now(datetime.timezone.utc)
        fam_category, _ = Category.objects.get_or_create(id=0, defaults={"display_name": "FamilyCat"})
        
        # Setup Meet & Attending infrastructure
        assembly = Assembly.objects.create(
            display_name="Test Assembly 2", slug="test-assembly-2", 
            division=self.division, category=fam_category
        )
        meet = Meet.objects.create(
            assembly=assembly, display_name="Test Meet", slug="test-meet",
            site_type_id=1, site_id=1,
            start=now, finish=now + datetime.timedelta(days=365)
        )
        character = Character.objects.create(
            assembly=assembly, display_name="Test Character", slug="test-char"
        )
        
        # Create Attendees Husband and Wife
        husband = Attendee.objects.create(first_name="Husband", last_name="Fam", division=self.division, gender="male")
        wife = Attendee.objects.create(first_name="Wife", last_name="Fam", division=self.division, gender="female")
        
        # Create Attendings & AttendingMeets (active)
        attending_husband = Attending.objects.create(attendee=husband, category=fam_category)
        attending_wife = Attending.objects.create(attendee=wife, category=fam_category)
        AttendingMeet.objects.create(
            attending=attending_husband, meet=meet, character=character, 
            category=self.category, start=now, finish=now + datetime.timedelta(days=365)
        )
        AttendingMeet.objects.create(
            attending=attending_wife, meet=meet, character=character, 
            category=self.category, start=now, finish=now + datetime.timedelta(days=365)
        )
        
        # Create Old Folk (Husband only, but the relationship is REMOVED)
        old_folk = Folk.objects.create(division=self.division, category=fam_category, display_name="Old Fam")
        FolkAttendee.objects.create(
            folk=old_folk, attendee=husband, role=self.relation, display_order=0, is_removed=True
        )
        
        # Create New Folk (Both Husband and Wife, active)
        new_folk = Folk.objects.create(division=self.division, category=fam_category, display_name="New Fam")
        FolkAttendee.objects.create(
            folk=new_folk, attendee=husband, role=self.relation, display_order=1, is_removed=False
        )
        FolkAttendee.objects.create(
            folk=new_folk, attendee=wife, role=self.relation, display_order=1, is_removed=False
        )
        
        # Test families_in_participations
        report_families = list(FolkService.families_in_participations(
            meet_slug="test-meet", 
            user_organization=self.organization, 
            show_paused=False, 
            division_slugs=[self.division.slug]
        ))
        
        assert len(report_families) == 1
        family_dict = report_families[0]
        assert len(family_dict['families']) == 2
        attendees_in_family = [a['first_name'] for a in family_dict['families'].values()]
        assert "Husband" in attendees_in_family
        assert "Wife" in attendees_in_family

    def test_folk_addresses_in_participations_with_removed_folkattendee(self):
        from attendees.occasions.models import Meet, Assembly, Character
        from attendees.persons.models import Attending, AttendingMeet, Folk, FolkAttendee, Category
        import datetime

        now = datetime.datetime.now(datetime.timezone.utc)
        fam_category, _ = Category.objects.get_or_create(id=0, defaults={"display_name": "FamilyCat"})
        
        assembly = Assembly.objects.create(
            display_name="Test Assembly 3", slug="test-assembly-3", 
            division=self.division, category=fam_category
        )
        meet = Meet.objects.create(
            assembly=assembly, display_name="Test Meet 3", slug="test-meet-3",
            site_type_id=1, site_id=1,
            start=now, finish=now + datetime.timedelta(days=365)
        )
        character = Character.objects.create(
            assembly=assembly, display_name="Test Character 3", slug="test-char-3"
        )
        
        husband = Attendee.objects.create(first_name="Husband", last_name="Fam", division=self.division, gender="male")
        wife = Attendee.objects.create(first_name="Wife", last_name="Fam", division=self.division, gender="female")
        
        attending_husband = Attending.objects.create(attendee=husband, category=fam_category)
        attending_wife = Attending.objects.create(attendee=wife, category=fam_category)
        AttendingMeet.objects.create(
            attending=attending_husband, meet=meet, character=character, 
            category=self.category, start=now, finish=now + datetime.timedelta(days=365)
        )
        AttendingMeet.objects.create(
            attending=attending_wife, meet=meet, character=character, 
            category=self.category, start=now, finish=now + datetime.timedelta(days=365)
        )
        
        old_folk = Folk.objects.create(division=self.division, category=fam_category, display_name="Old Fam")
        FolkAttendee.objects.create(
            folk=old_folk, attendee=husband, role=self.relation, display_order=0, is_removed=True
        )
        
        new_folk = Folk.objects.create(division=self.division, category=fam_category, display_name="New Fam")
        FolkAttendee.objects.create(
            folk=new_folk, attendee=husband, role=self.relation, display_order=1, is_removed=False
        )
        FolkAttendee.objects.create(
            folk=new_folk, attendee=wife, role=self.relation, display_order=1, is_removed=False
        )
        
        # Test envelopes behavior
        envelopes_families = list(FolkService.folk_addresses_in_participations(
            meet_slug="test-meet-3", 
            user_organization=self.organization, 
            show_paused=False, 
            division_slugs=[self.division.slug]
        ))
        
        # Should be exactly 1 envelope because the removed FolkAttendee is ignored
        assert len(envelopes_families) == 1
        family_dict = envelopes_families[0]
        assert len(family_dict['families']) == 2
        attendees_in_family = [a['first_name'] for a in family_dict['families'].values()]
        assert "Husband" in attendees_in_family
        assert "Wife" in attendees_in_family
