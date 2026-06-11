import pytest
from datetime import datetime, timedelta, timezone
from django.contrib.contenttypes.models import ContentType
from attendees.whereabouts.models import Organization, Division, Room
from attendees.occasions.models import Assembly, Character, Meet, Gathering
from attendees.persons.models import Category
from django.contrib.auth.models import Group
from schedule.models import Event, Calendar, EventRelation, Occurrence

@pytest.mark.django_db
class TestOccasionsSignals:
    def setup_method(self):
        self.organization = Organization.objects.create(display_name="Test Org", slug="test-org")
        self.group = Group.objects.create(name="Test Group")
        self.division = Division.objects.create(
            organization=self.organization,
            display_name="Test Div",
            slug="test-div",
            audience_auth_group=self.group
        )
        self.category = Category.objects.create(id=25, display_name="Test Cat")
        self.assembly = Assembly.objects.create(
            display_name="Test Assembly",
            slug="test-assembly",
            division=self.division,
            category=self.category,
        )
        self.character = Character.objects.create(
            assembly=self.assembly,
            display_name="Test Char",
            slug="test-char",
            type="normal",
        )
        self.room = Room.objects.create(display_name="Room A", slug="room-a")
        self.site_type = ContentType.objects.get_for_model(Room)
        
        self.now = datetime.now(timezone.utc)
        self.calendar = Calendar.objects.create(name='test_cal', slug='test_cal')
        self.event = Event.objects.create(
            start=self.now,
            end=self.now + timedelta(hours=2),
            title='test event',
            calendar=self.calendar
        )
        
        # Create Meet
        self.meet = Meet.objects.create(
            assembly=self.assembly,
            major_character=self.character,
            shown_audience=True,
            audience_editable=True,
            start=self.now,
            finish=self.now + timedelta(days=10),
            display_name="Test Meet",
            slug="test-meet",
            site_type=self.site_type,
            site_id=str(self.room.id),
        )

        # Create relation between meet and event (source)
        self.event_relation = EventRelation.objects.create(
            event=self.event,
            content_type=ContentType.objects.get_for_model(self.meet),
            object_id=self.meet.id,
            distinction='source'
        )

    def test_post_save_handler_for_gathering_to_update_occurrence_create(self):
        # When creating a gathering, an occurrence should be auto-created
        gathering = Gathering.objects.create(
            meet=self.meet,
            start=self.now,
            finish=self.now + timedelta(hours=2),
            display_name="Test Gathering",
            site_type=self.site_type,
            site_id=str(self.room.id),
        )
        
        # An occurrence should now exist for this gathering
        occurrences = list(gathering.occurrences())
        assert len(occurrences) == 1
        assert occurrences[0].title == f"gathering#{gathering.id}"
        assert occurrences[0].description == f"room#{self.room.id}"

    def test_post_save_handler_for_gathering_to_update_occurrence_update(self):
        # Create initial gathering
        gathering = Gathering.objects.create(
            meet=self.meet,
            start=self.now,
            finish=self.now + timedelta(hours=2),
            display_name="Test Gathering",
            site_type=self.site_type,
            site_id=str(self.room.id),
        )
        
        occurrences = list(gathering.occurrences())
        assert len(occurrences) == 1
        initial_end = occurrences[0].end
        
        # Now update the gathering's finish time
        gathering.finish = self.now + timedelta(hours=3)
        gathering.save()
        
        # The occurrence should be updated
        updated_occurrences = list(gathering.occurrences())
        assert len(updated_occurrences) == 1
        assert updated_occurrences[0].end > initial_end

    def test_post_save_handler_for_gathering_to_update_occurrence_delete(self):
        gathering = Gathering.objects.create(
            meet=self.meet,
            start=self.now,
            finish=self.now + timedelta(hours=2),
            display_name="Test Gathering",
            site_type=self.site_type,
            site_id=str(self.room.id),
        )
        
        occurrence_id = list(gathering.occurrences())[0].id
        assert Occurrence.objects.filter(id=occurrence_id).exists()
        
        # Soft delete the gathering
        gathering.is_removed = True
        gathering.save()
        
        # The occurrence should be hard deleted by the signal
        assert not Occurrence.objects.filter(id=occurrence_id).exists()

    def test_post_save_handler_for_gathering_skip_batch_created(self):
        # When creating a gathering with 'batch created', it should NOT auto-create an occurrence
        gathering = Gathering.objects.create(
            meet=self.meet,
            start=self.now,
            finish=self.now + timedelta(hours=2),
            display_name="Test Gathering",
            site_type=self.site_type,
            site_id=str(self.room.id),
            infos={'created_reason': 'batch created'}
        )
        
        occurrences = list(gathering.occurrences())
        assert len(occurrences) == 0

    def test_post_save_handler_for_meet_to_update_event_location(self):
        # We already have a source event_relation created in setup
        
        # Create a location event relation
        location_event = Event.objects.create(
            start=self.now,
            end=self.now + timedelta(hours=2),
            title='location event',
            calendar=self.calendar
        )
        EventRelation.objects.create(
            event=location_event,
            content_type=ContentType.objects.get_for_model(self.meet),
            object_id=self.meet.id,
            distinction='location'
        )
        
        # Trigger meet save
        new_finish = self.now + timedelta(days=20)
        self.meet.finish = new_finish
        self.meet.save()
        
        # The source event should have its end_recurring_period and description updated
        self.event.refresh_from_db()
        assert self.event.end_recurring_period == new_finish
        assert self.event.description == f"room#{self.room.id}"
        
        # The location event should have its title, end_recurring_period and description updated
        location_event.refresh_from_db()
        assert location_event.end_recurring_period == new_finish
        assert location_event.title == f"event#{self.event.id}"
        assert location_event.description == f"room#{self.room.id}"