import pytest
from unittest.mock import MagicMock, patch

from attendees.users.authorization.peek_other import PeekOther


class TestPeekOther:
    def test_get_attendee_or_self_with_no_attendee_id(self):
        current_user = MagicMock()
        current_user.attendee = "my_attendee"
        
        result = PeekOther.get_attendee_or_self(current_user, None)
        assert result == "my_attendee"

    def test_get_attendee_or_self_no_user_attendee(self):
        current_user = MagicMock(spec=[])  # no attendee attribute
        
        result = PeekOther.get_attendee_or_self(current_user, None)
        assert result is None

    @patch("attendees.users.authorization.peek_other.Attendee")
    def test_get_attendee_or_self_not_privileged(self, mock_attendee):
        current_user = MagicMock()
        current_user.attendee = "my_attendee"
        current_user.privileged = False
        
        result = PeekOther.get_attendee_or_self(current_user, "123")
        assert result == "my_attendee"
        mock_attendee.objects.filter.assert_not_called()

    @patch("attendees.users.authorization.peek_other.Attendee")
    def test_get_attendee_or_self_privileged_other_not_found(self, mock_attendee):
        current_user = MagicMock()
        current_user.attendee = "my_attendee"
        current_user.privileged = True
        
        mock_qs = MagicMock()
        mock_qs.first.return_value = None
        mock_attendee.objects.filter.return_value = mock_qs
        
        result = PeekOther.get_attendee_or_self(current_user, "123")
        assert result == "my_attendee"
        mock_attendee.objects.filter.assert_called_once_with(pk="123")

    @patch("attendees.users.authorization.peek_other.Attendee")
    def test_get_attendee_or_self_privileged_other_found(self, mock_attendee):
        current_user = MagicMock()
        current_user.attendee = "my_attendee"
        current_user.privileged = True
        
        mock_qs = MagicMock()
        mock_qs.first.return_value = "other_attendee"
        mock_attendee.objects.filter.return_value = mock_qs
        
        result = PeekOther.get_attendee_or_self(current_user, "123")
        assert result == "other_attendee"
        mock_attendee.objects.filter.assert_called_once_with(pk="123")
