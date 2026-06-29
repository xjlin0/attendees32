import pytest
from unittest.mock import patch, MagicMock
from attendees.persons.serializers.attending_minimal_serializer import AttendingMinimalSerializer

@pytest.mark.django_db
class TestAttendingMinimalSerializer:
    @patch('attendees.persons.serializers.attending_minimal_serializer.Registration')
    @patch('attendees.persons.serializers.attending_minimal_serializer.Attending')
    def test_create_with_registration(self, mock_attending, mock_registration):
        mock_reg_instance = MagicMock(id=1)
        mock_registration.objects.update_or_create.return_value = (mock_reg_instance, True)
        mock_attending.objects.update_or_create.return_value = (MagicMock(id=1), True)

        data = {
            "registration": {
                "assembly": 1,
                "registrant": 1,
                "some_key": "value"
            },
            "category": "test",
            "infos": {}
        }

        serializer = AttendingMinimalSerializer()
        result = serializer.create(data)

        mock_registration.objects.update_or_create.assert_called_once_with(
            defaults={'assembly': 1, 'registrant': 1, 'some_key': 'value'},
            assembly=1,
            registrant=1
        )
        mock_attending.objects.update_or_create.assert_called_once_with(
            id=None,
            defaults={"category": "test", "infos": {}, "registration": mock_reg_instance}
        )

    @patch('attendees.persons.serializers.attending_minimal_serializer.Registration')
    @patch('attendees.persons.serializers.attending_minimal_serializer.Attending')
    def test_update_with_registration(self, mock_attending, mock_registration):
        mock_reg_instance = MagicMock(id=1)
        mock_registration.objects.update_or_create.return_value = (mock_reg_instance, False)
        mock_attending.objects.update_or_create.return_value = (MagicMock(id=1), False)

        instance = MagicMock(id=2)
        instance.registration = MagicMock(id=1)

        data = {
            "registration": {
                "assembly": 1,
                "registrant": 1,
            },
            "category": "updated"
        }

        serializer = AttendingMinimalSerializer()
        result = serializer.update(instance, data)

        mock_registration.objects.update_or_create.assert_called_once_with(
            defaults={'assembly': 1, 'registrant': 1},
            id=1,
            assembly=1,
            registrant=1
        )
        mock_attending.objects.update_or_create.assert_called_once_with(
            id=2,
            defaults={"category": "updated", "registration": mock_reg_instance}
        )
