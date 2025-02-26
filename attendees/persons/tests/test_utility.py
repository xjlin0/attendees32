import pytest, pytz
from datetime import datetime, timedelta, timezone
from django.conf import settings
from attendees.persons.models import Utility

class TestUtility:
    def test_present_check(self):
        assert Utility.present_check("test") is True
        assert Utility.present_check("  ") is False
        assert Utility.present_check("") is False

    def test_blank_check(self):
        assert Utility.blank_check("test") is False
        assert Utility.blank_check("  ") is True
        assert Utility.blank_check("") is True

    def test_phone_number_formatter(self):
        assert Utility.phone_number_formatter("+11234567890") == "(123)456-7890"
        assert Utility.phone_number_formatter("") == ""

    def test_user_infos(self):
        assert Utility.user_infos() == {"settings": {}}

    def test_default_infos(self):
        assert Utility.default_infos() == {"fixed": {}, "contacts": {}}

    def test_organization_infos(self):
        infos = Utility.organization_infos()
        assert infos["acronym"] == "change me in infos"
        assert infos["default_time_zone"] == settings.CLIENT_DEFAULT_TIME_ZONE
        assert "settings" in infos
        assert "contacts" in infos

    def test_attendee_infos(self):
        infos = Utility.attendee_infos()
        assert "names" in infos
        assert "fixed" in infos
        assert infos["fixed"]["mobility"] == 2

    def test_folk_infos(self):
        assert Utility.folk_infos() == {"print_directory": False}

    def test_meet_infos(self):
        infos = Utility.meet_infos()
        assert "allowed_models" in infos
        assert infos["allowed_models"] == ['gathering', 'attendingmeet', 'attendance', 'eventrelation']
        assert "default_time_zone" in infos
        assert infos["default_time_zone"] == settings.CLIENT_DEFAULT_TIME_ZONE

    def test_relationship_infos(self):
        infos = Utility.relationship_infos()
        assert "show_secret" in infos
        assert "updating_attendees" in infos

    def test_forever(self):
        forever_date = Utility.forever()
        expected_date = datetime.now(timezone.utc) + timedelta(weeks=99999)
        assert forever_date.year == expected_date.year

    def test_now_with_timezone(self):
        now = Utility.now_with_timezone()
        assert now.tzinfo is not None

    def test_today_string(self):
        today = Utility.today_string()
        expected_today = datetime.now(pytz.timezone(settings.CLIENT_DEFAULT_TIME_ZONE)).strftime('%Y-%m-%d')
        assert today == expected_today

    def test_is_truthy(self):
        assert Utility.is_truthy("1") is True
        assert Utility.is_truthy(1) is True
        assert Utility.is_truthy("True") is True
        assert Utility.is_truthy(True) is True
        assert Utility.is_truthy("true") is True
        assert Utility.is_truthy("0") is False

    def test_presence(self):
        assert Utility.presence("test") == "test"
        assert Utility.presence("  ") is None
        assert Utility.presence("") is None

    def test_boolean_or_datetext_or_original(self):
        assert Utility.boolean_or_datetext_or_original("TRUE") is True
        assert Utility.boolean_or_datetext_or_original("FALSE") is False
        assert Utility.boolean_or_datetext_or_original("1") is True
        assert Utility.boolean_or_datetext_or_original("0") is False
        assert Utility.boolean_or_datetext_or_original("12/31/2025") == "2025-12-31"
        assert Utility.boolean_or_datetext_or_original("test") == "test"
        assert Utility.boolean_or_datetext_or_original(1) is True
        assert Utility.boolean_or_datetext_or_original(0) is False

    def test_underscore(self):
        assert Utility.underscore("CamelCase") == "camel_case"
        assert Utility.underscore("lowerCase") == "lower_case"
