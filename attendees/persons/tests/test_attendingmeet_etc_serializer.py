import pytest
from unittest.mock import patch, MagicMock
from attendees.persons.serializers.attendingmeet_etc_serializer import AttendingMeetEtcSerializer

@pytest.mark.django_db
class TestAttendingMeetEtcSerializer:
    @patch('attendees.persons.serializers.attendingmeet_etc_serializer.AttendingMeet')
    def test_create(self, mock_attending_meet):
        mock_attending_meet.objects.update_or_create.return_value = (MagicMock(id=1), True)
        
        serializer = AttendingMeetEtcSerializer()
        serializer._kwargs = {"data": {"id": 1}}
        
        result = serializer.create({"start": "2021-01-01"})
        
        mock_attending_meet.objects.update_or_create.assert_called_once_with(
            id=1,
            defaults={"start": "2021-01-01"}
        )

    def test_update(self):
        instance = MagicMock()
        instance.meet = MagicMock()
        instance.infos = {"existing": "value"}
        
        serializer = AttendingMeetEtcSerializer()
        data = {
            "start": "2021-01-01",
            "infos": {"new": "value"}
        }
        
        result = serializer.update(instance, data)
        
        assert instance.start == "2021-01-01"
        assert instance.infos == {"existing": "value", "new": "value"}
        instance.meet.save.assert_called_once()
        instance.save.assert_called_once()
