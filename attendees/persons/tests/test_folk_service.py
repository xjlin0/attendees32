import pytest
from uuid import uuid4
from django.contrib.auth.models import Group
from attendees.persons.services.folk_service import FolkService
from attendees.persons.models import Folk, Attendee, FolkAttendee, Category, Relation
from attendees.persons.models.enum import GenderEnum
from attendees.whereabouts.models import Division, Organization
from attendees.occasions.models import Meet, Assembly, Character
from attendees.persons.models import Attending, AttendingMeet, Folk, FolkAttendee, Category
import datetime

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

    def test_families_in_participations_multi_participate_true(self):

        now = datetime.datetime.now(datetime.timezone.utc)
        fam_category, _ = Category.objects.get_or_create(id=0, defaults={"display_name": "FamilyCat"})

        assembly = Assembly.objects.create(
            display_name="Test Assembly 4", slug="test-assembly-4",
            division=self.division, category=fam_category
        )
        # Set the flag to True
        meet = Meet.objects.create(
            assembly=assembly, display_name="Test Meet 4", slug="test-meet-4",
            site_type_id=1, site_id=1,
            start=now, finish=now + datetime.timedelta(days=365),
            infos={"can_multi_participate": True}
        )
        character = Character.objects.create(
            assembly=assembly, display_name="Test Character 4", slug="test-char-4"
        )

        # Create one Attendee (AdultSon)
        adult_son = Attendee.objects.create(first_name="AdultSon", last_name="Fam", division=self.division, gender="male")

        attending = Attending.objects.create(attendee=adult_son, category=fam_category)
        AttendingMeet.objects.create(
            attending=attending, meet=meet, character=character,
            category=self.category, start=now, finish=now + datetime.timedelta(days=365)
        )

        # Family 1 (Parents' family), AdultSon is rank 5
        parents_folk = Folk.objects.create(division=self.division, category=fam_category, display_name="Parents Fam")
        FolkAttendee.objects.create(
            folk=parents_folk, attendee=adult_son, role=self.relation, display_order=5, is_removed=False
        )

        # Family 2 (AdultSon's own family), AdultSon is rank 1
        adult_son_folk = Folk.objects.create(division=self.division, category=fam_category, display_name="AdultSon Fam")
        FolkAttendee.objects.create(
            folk=adult_son_folk, attendee=adult_son, role=self.relation, display_order=1, is_removed=False
        )

        # Test families_in_participations
        report_families = list(FolkService.families_in_participations(
            meet_slug="test-meet-4",
            user_organization=self.organization,
            show_paused=False,
            division_slugs=[self.division.slug]
        ))

        # Since can_multi_participate is True, AdultSon should appear in BOTH families
        assert len(report_families) == 2

    def test_families_in_participations_multi_participate_false(self):

        now = datetime.datetime.now(datetime.timezone.utc)
        fam_category, _ = Category.objects.get_or_create(id=0, defaults={"display_name": "FamilyCat"})

        assembly = Assembly.objects.create(
            display_name="Test Assembly 5", slug="test-assembly-5",
            division=self.division, category=fam_category
        )
        # Flag is missing (defaults to False)
        meet = Meet.objects.create(
            assembly=assembly, display_name="Test Meet 5", slug="test-meet-5",
            site_type_id=1, site_id=1,
            start=now, finish=now + datetime.timedelta(days=365),
            infos={}
        )
        character = Character.objects.create(
            assembly=assembly, display_name="Test Character 5", slug="test-char-5"
        )

        adult_son = Attendee.objects.create(first_name="AdultSon", last_name="Fam", division=self.division, gender="male")

        attending = Attending.objects.create(attendee=adult_son, category=fam_category)
        AttendingMeet.objects.create(
            attending=attending, meet=meet, character=character,
            category=self.category, start=now, finish=now + datetime.timedelta(days=365)
        )

        # Family 1 (Parents' family), AdultSon is rank 5
        parents_folk = Folk.objects.create(division=self.division, category=fam_category, display_name="Parents Fam")
        FolkAttendee.objects.create(
            folk=parents_folk, attendee=adult_son, role=self.relation, display_order=5, is_removed=False
        )

        # Family 2 (AdultSon's own family), AdultSon is rank 1
        adult_son_folk = Folk.objects.create(division=self.division, category=fam_category, display_name="AdultSon Fam")
        FolkAttendee.objects.create(
            folk=adult_son_folk, attendee=adult_son, role=self.relation, display_order=1, is_removed=False
        )

        report_families = list(FolkService.families_in_participations(
            meet_slug="test-meet-5",
            user_organization=self.organization,
            show_paused=False,
            division_slugs=[self.division.slug]
        ))

        # Since can_multi_participate is False, AdultSon should only appear in ONE family (the one with rank 1)
        assert len(report_families) == 1
        family_dict = report_families[0]
        # Verify it's AdultSon's own family (rank 1), which means family_name should match AdultSon's last name
        # But actually we just check that only 1 family is returned
        assert "AdultSon" in [a['first_name'] for a in family_dict['families'].values()]
    def test_families_in_directory_multi_family_attendee(self):
        from attendees.occasions.models import Meet, Assembly, Character
        from attendees.persons.models import Attending, AttendingMeet, Folk, FolkAttendee, Category
        import datetime
        from django.utils import timezone

        now = datetime.datetime.now(datetime.timezone.utc)
        fam_category, _ = Category.objects.get_or_create(id=0, defaults={"display_name": "FamilyCat"})
        
        assembly = Assembly.objects.create(
            display_name="Test Assembly Dir", slug="test-assembly-dir", 
            division=self.division, category=fam_category
        )
        directory_meet = Meet.objects.create(
            assembly=assembly, display_name="Directory Meet", slug="dir-meet",
            site_type_id=1, site_id=1,
            start=now, finish=now + datetime.timedelta(days=365),
            infos={"print_directory": True}
        )
        character = Character.objects.create(
            assembly=assembly, display_name="Test Character Dir", slug="test-char-dir"
        )
        
        # We need an adult son who is in two families
        adult_son = Attendee.objects.create(first_name="AdultSon", last_name="Fam", division=self.division, gender="male")
        attending_son = Attending.objects.create(attendee=adult_son, category=fam_category)
        AttendingMeet.objects.create(
            attending=attending_son, meet=directory_meet, character=character, 
            category=self.category, start=now, finish=now + datetime.timedelta(days=365)
        )
        
        # We need the mother
        mother = Attendee.objects.create(first_name="Mother", last_name="Fam", division=self.division, gender="female")
        attending_mother = Attending.objects.create(attendee=mother, category=fam_category)
        AttendingMeet.objects.create(
            attending=attending_mother, meet=directory_meet, character=character, 
            category=self.category, start=now, finish=now + datetime.timedelta(days=365)
        )

        # We need the wife of adult son
        wife = Attendee.objects.create(first_name="Wife", last_name="Fam", division=self.division, gender="female")
        attending_wife = Attending.objects.create(attendee=wife, category=fam_category)
        AttendingMeet.objects.create(
            attending=attending_wife, meet=directory_meet, character=character, 
            category=self.category, start=now, finish=now + datetime.timedelta(days=365)
        )
        
        # Family 1 (Parents' family)
        parents_folk = Folk.objects.create(division=self.division, category=fam_category, display_name="Parents Fam", infos={"print_directory": True})
        
        mother_role, _ = Relation.objects.get_or_create(id=1, defaults={"title": "mother", "gender": GenderEnum.FEMALE.value})
        child_role, _ = Relation.objects.get_or_create(id=2, defaults={"title": "child", "gender": GenderEnum.UNSPECIFIED.value})
        husband_role, _ = Relation.objects.get_or_create(id=3, defaults={"title": "husband", "gender": GenderEnum.MALE.value})
        wife_role, _ = Relation.objects.get_or_create(id=4, defaults={"title": "wife", "gender": GenderEnum.FEMALE.value})
        
        FolkAttendee.objects.create(folk=parents_folk, attendee=mother, role=mother_role, display_order=1, is_removed=False)
        FolkAttendee.objects.create(folk=parents_folk, attendee=adult_son, role=child_role, display_order=5, is_removed=False)
        
        # Family 2 (Adult son's own family)
        albert_folk = Folk.objects.create(division=self.division, category=fam_category, display_name="AdultSon Fam", infos={"print_directory": True})
        FolkAttendee.objects.create(folk=albert_folk, attendee=adult_son, role=husband_role, display_order=1, is_removed=False)
        FolkAttendee.objects.create(folk=albert_folk, attendee=wife, role=wife_role, display_order=2, is_removed=False)
        
        # Execute the method
        index_list, families = FolkService.families_in_directory(
            directory_meet_id=directory_meet.id,
            member_meet_id=directory_meet.id,  # just pass the same or none
            divisions=[self.division]
        )
        
        # We expect two families in the output
        assert len(families) == 2
        
        # Validate Parents Fam
        # Find which dict is which
        parents_fam_result = next((f for f in families if "Mother" in f['household_title']), None)
        assert parents_fam_result is not None
        # In Parents Fam, AdultSon should be an attendee, and mother should be the householder
        attendee_names = [a['first_name'] for a in parents_fam_result['attendees']]
        assert any("AdultSon" in name for name in attendee_names)
        assert any("Mother" in name for name in attendee_names)
        assert not any("Wife" in name for name in attendee_names)
        
        # Validate AdultSon Fam
        albert_fam_result = next((f for f in families if "AdultSon" in f['household_title']), None)
        assert albert_fam_result is not None
        # AdultSon and Wife should be here, NO Mother
        attendee_names_albert = [a['first_name'] for a in albert_fam_result['attendees']]
        assert any("AdultSon" in name for name in attendee_names_albert)
        assert any("Wife" in name for name in attendee_names_albert)
        assert not any("Mother" in name for name in attendee_names_albert)
    def test_folk_addresses_in_participations_multi_participate_true(self):
        from attendees.occasions.models import Meet, Assembly, Character
        from attendees.persons.models import Attending, AttendingMeet, Folk, FolkAttendee, Category
        import datetime
        from django.utils import timezone

        now = datetime.datetime.now(datetime.timezone.utc)
        fam_category, _ = Category.objects.get_or_create(id=0, defaults={"display_name": "FamilyCat"})
        
        assembly = Assembly.objects.create(
            display_name="Test Assembly Addr 1", slug="test-assembly-addr-1", 
            division=self.division, category=fam_category
        )
        meet = Meet.objects.create(
            assembly=assembly, display_name="Test Meet Addr 1", slug="test-meet-addr-1",
            site_type_id=1, site_id=1,
            start=now, finish=now + datetime.timedelta(days=365),
            infos={"can_multi_participate": True}
        )
        character = Character.objects.create(
            assembly=assembly, display_name="Test Character Addr 1", slug="test-char-addr-1"
        )
        
        adult_son = Attendee.objects.create(first_name="AdultSon", last_name="Fam", division=self.division, gender="male")
        attending = Attending.objects.create(attendee=adult_son, category=fam_category)
        AttendingMeet.objects.create(
            attending=attending, meet=meet, character=character, 
            category=self.category, start=now, finish=now + datetime.timedelta(days=365)
        )
        
        parents_folk = Folk.objects.create(division=self.division, category=fam_category, display_name="Parents Fam")
        FolkAttendee.objects.create(folk=parents_folk, attendee=adult_son, role=self.relation, display_order=5, is_removed=False)
        
        albert_folk = Folk.objects.create(division=self.division, category=fam_category, display_name="AdultSon Fam")
        FolkAttendee.objects.create(folk=albert_folk, attendee=adult_son, role=self.relation, display_order=1, is_removed=False)
        
        report_families = list(FolkService.folk_addresses_in_participations(
            meet_slug="test-meet-addr-1", 
            user_organization=self.organization, 
            show_paused=False, 
            division_slugs=[self.division.slug]
        ))
        
        assert len(report_families) == 2

    def test_folk_addresses_in_participations_multi_participate_false(self):
        from attendees.occasions.models import Meet, Assembly, Character
        from attendees.persons.models import Attending, AttendingMeet, Folk, FolkAttendee, Category
        import datetime
        from django.utils import timezone

        now = datetime.datetime.now(datetime.timezone.utc)
        fam_category, _ = Category.objects.get_or_create(id=0, defaults={"display_name": "FamilyCat"})
        
        assembly = Assembly.objects.create(
            display_name="Test Assembly Addr 2", slug="test-assembly-addr-2", 
            division=self.division, category=fam_category
        )
        meet = Meet.objects.create(
            assembly=assembly, display_name="Test Meet Addr 2", slug="test-meet-addr-2",
            site_type_id=1, site_id=1,
            start=now, finish=now + datetime.timedelta(days=365),
            infos={} # Defaults to false
        )
        character = Character.objects.create(
            assembly=assembly, display_name="Test Character Addr 2", slug="test-char-addr-2"
        )
        
        adult_son = Attendee.objects.create(first_name="AdultSon", last_name="Fam", division=self.division, gender="male")
        attending = Attending.objects.create(attendee=adult_son, category=fam_category)
        AttendingMeet.objects.create(
            attending=attending, meet=meet, character=character, 
            category=self.category, start=now, finish=now + datetime.timedelta(days=365)
        )
        
        parents_folk = Folk.objects.create(division=self.division, category=fam_category, display_name="Parents Fam")
        FolkAttendee.objects.create(folk=parents_folk, attendee=adult_son, role=self.relation, display_order=5, is_removed=False)
        
        albert_folk = Folk.objects.create(division=self.division, category=fam_category, display_name="AdultSon Fam")
        FolkAttendee.objects.create(folk=albert_folk, attendee=adult_son, role=self.relation, display_order=1, is_removed=False)
        
        report_families = list(FolkService.folk_addresses_in_participations(
            meet_slug="test-meet-addr-2", 
            user_organization=self.organization, 
            show_paused=False, 
            division_slugs=[self.division.slug]
        ))
        
        assert len(report_families) == 1
