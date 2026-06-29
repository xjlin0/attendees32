import pytest
from unittest.mock import patch, MagicMock
from attendees.persons.serializers.folk_attendee_serializer import FolkAttendeeSerializer

@pytest.mark.django_db
class TestFolkAttendeeSerializer:
    @patch('attendees.persons.serializers.folk_attendee_serializer.Folk')
    @patch('attendees.persons.serializers.folk_attendee_serializer.FolkAttendee')
    def test_create(self, mock_folk_attendee, mock_folk):
        mock_folk_instance = MagicMock(id=1)
        mock_folk.objects.filter.return_value.first.return_value = mock_folk_instance
        mock_folk_attendee.objects.update_or_create.return_value = (MagicMock(id=1), True)
        
        serializer = FolkAttendeeSerializer()
        serializer._kwargs = {"data": {"id": 1, "folk": 1}}
        
        result = serializer.create({"some_data": "value"})
        
        mock_folk.objects.filter.assert_called_once_with(pk=1)
        mock_folk_attendee.objects.update_or_create.assert_called_once_with(
            id=1,
            defaults={"some_data": "value", "folk": mock_folk_instance}
        )

    @patch('attendees.persons.serializers.folk_attendee_serializer.Folk')
    @patch('attendees.persons.serializers.folk_attendee_serializer.FolkAttendee')
    def test_update(self, mock_folk_attendee, mock_folk):
        mock_folk_instance = MagicMock(id=2)
        mock_folk.objects.filter.return_value.first.return_value = mock_folk_instance
        mock_folk_attendee.objects.update_or_create.return_value = (MagicMock(id=1), False)
        
        instance = MagicMock(id=1)
        serializer = FolkAttendeeSerializer()
        serializer._kwargs = {"data": {"folk": {"id": 2}}}
        
        result = serializer.update(instance, {"some_data": "updated"})
        
        mock_folk.objects.filter.assert_called_once_with(pk=2)
        mock_folk_attendee.objects.update_or_create.assert_called_once_with(
            id=1,
            defaults={"some_data": "updated", "folk": mock_folk_instance}
        )
