import pytest
from unittest.mock import patch, MagicMock
from attendees.persons.serializers.attendee_minimal_serializer import AttendeeMinimalSerializer

@pytest.mark.django_db
class TestAttendeeMinimalSerializer:
    @patch('attendees.persons.serializers.attendee_minimal_serializer.Attendee')
    def test_create(self, mock_attendee):
        mock_attendee.objects.create.return_value = MagicMock(id=1)
        data = {"first_name": "John"}
        
        serializer = AttendeeMinimalSerializer()
        result = serializer.create(data)
        
        mock_attendee.objects.create.assert_called_once_with(**data)

    @patch('attendees.persons.serializers.attendee_minimal_serializer.Attendee')
    @patch('attendees.persons.serializers.attendee_minimal_serializer.Path')
    def test_update_with_photo_clear(self, mock_path, mock_attendee):
        mock_attendee.objects.update_or_create.return_value = (MagicMock(id=1), False)
        
        instance = MagicMock(id=1)
        instance.photo = MagicMock()
        instance.photo.path = "old/photo.jpg"
        
        serializer = AttendeeMinimalSerializer()
        serializer._kwargs = {"data": {"photo-clear": True}}
        
        result = serializer.update(instance, {})
        
        mock_path.assert_called_once_with("old/photo.jpg")
        mock_path.return_value.unlink.assert_called_once_with(missing_ok=True)
        mock_attendee.objects.update_or_create.assert_called_once_with(
            id=1,
            defaults={"photo": None}
        )
