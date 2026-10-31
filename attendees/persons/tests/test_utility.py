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

    def test_normalize_phone_number(self):
        assert Utility.normalize_phone_number("510-123-4567") == "+15101234567"
        assert Utility.normalize_phone_number("(510) 123-4567") == "+15101234567"
        assert Utility.normalize_phone_number("15101234567") == "+15101234567"
        assert Utility.normalize_phone_number("+886912345678") == "+886912345678"
        assert Utility.normalize_phone_number("510123456789") == "+10123456789"
        assert Utility.normalize_phone_number("12345") == "12345"
        assert Utility.normalize_phone_number("") == ""
        assert Utility.normalize_phone_number(None) is None
        assert Utility.normalize_phone_number(123) == 123

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

    def test_get_model_by_name(self):
        from attendees.whereabouts.models import Place
        from attendees.persons.models import Attendee
        assert Utility.get_model_by_name("place") == Place
        assert Utility.get_model_by_name("attendee") == Attendee
        assert Utility.get_model_by_name("nonexistent_model_xyz") is None
        assert Utility.get_model_by_name("") is None

    @pytest.mark.django_db
    def test_get_object_name_without_content_type_query(self, django_assert_num_queries):
        from unittest.mock import MagicMock
        from attendees.whereabouts.models import Place, Organization
        from django.contrib.contenttypes.models import ContentType
        org = Organization.objects.create(slug="test-util-org", display_name="Test Util Org")
        place = Place.objects.create(
            organization=org,
            content_type=ContentType.objects.get_for_model(Organization),
            object_id=str(org.id),
            display_name="Sanctuary",
        )
        fake_event = MagicMock()
        fake_event.description = f"place#{place.id}"

        # First call populates model cache
        Utility.get_object_name(fake_event, object_field='display_name')

        # Subsequent call with object_field should query only the target table (Place), NEVER django_content_type
        with django_assert_num_queries(1):
            name = Utility.get_object_name(fake_event, object_field='display_name')
            assert name == "Sanctuary"

    def test_merge_contacts_deduplication_and_strictly_numbered_keys(self):
        # 1. Deduplication across different keys
        existing = {"phone1": "+15101112222", "phone2": "+15103334444"}
        incoming = {"phone1": "(510) 333-4444"}  # matches phone2
        merged = Utility.merge_contacts(existing, incoming)
        assert merged == {"phone1": "+15101112222", "phone2": "+15103334444"}
        assert "phone" not in merged

        # 2. Append new phone without overwriting
        incoming_new = {"phone1": "510-777-8888"}
        merged2 = Utility.merge_contacts(existing, incoming_new)
        assert merged2 == {
            "phone1": "+15101112222",
            "phone2": "+15103334444",
            "phone3": "+15107778888",
        }
        assert "phone" not in merged2

        # 3. Email deduplication with case-insensitivity
        existing_email = {"email1": "John@Example.COM"}
        incoming_email = {"email1": "john@example.com", "email2": "work@company.com"}
        merged_email = Utility.merge_contacts(existing_email, incoming_email)
        assert merged_email == {
            "email1": "John@Example.COM",
            "email2": "work@company.com",
        }
        assert "email" not in merged_email

        # 4. Multi-type contacts: wechat, line, whatsapp
        existing_multi = {"wechat1": "wx_john", "phone1": "+15101112222"}
        incoming_multi = {"line1": "line_john", "wechat1": "wx_john", "whatsapp1": "5101112222"}
        merged_multi = Utility.merge_contacts(existing_multi, incoming_multi)
        assert merged_multi == {
            "line1": "line_john",
            "phone1": "+15101112222",
            "wechat1": "wx_john",
            "whatsapp1": "+15101112222",
        }

        # 5. Legacy unnumbered keys in existing dict get cleaned up to numbered keys
        legacy_existing = {"phone": "+15101112222", "email": "a@b.com"}
        cleaned = Utility.merge_contacts(legacy_existing, {})
        assert cleaned == {"phone1": "+15101112222", "email1": "a@b.com"}
        assert "phone" not in cleaned
        assert "email" not in cleaned

    def test_deep_merge_attendee_infos(self):
        existing_infos = {
            "fixed": {"food_pref": "Peanuts allergy", "mobility": 2, "grade": 1},
            "contacts": {"phone1": "+15101112222"},
            "emergency_contacts": {"101": True},
        }
        new_infos = {
            "fixed": {"grade": 2, "food_pref": ""},  # empty food_pref should NOT wipe existing
            "contacts": {"phone1": "+15109990000", "email1": "kid@example.com"},
            "emergency_contacts": {"102": True},
        }
        merged = Utility.deep_merge_attendee_infos(existing_infos, new_infos, current_user_attendee_id="admin-999")

        assert merged["fixed"]["mobility"] == 2
        assert merged["fixed"]["food_pref"] == "Peanuts allergy"
        assert merged["fixed"]["grade"] == 2

        assert merged["contacts"]["phone1"] == "+15101112222"
        assert merged["contacts"]["phone2"] == "+15109990000"
        assert merged["contacts"]["email1"] == "kid@example.com"
        assert "phone" not in merged["contacts"]

        assert merged["emergency_contacts"] == {"101": True, "102": True}
        assert "admin-999" in merged["updating_attendees"]
