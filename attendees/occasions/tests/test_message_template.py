import pytest
from attendees.occasions.models.message_template import MessageTemplate
from attendees.whereabouts.models import Organization

pytestmark = pytest.mark.django_db


def test_create_message_template():
    org = Organization.objects.create(display_name="Test Org", slug="test-org")
    mt = MessageTemplate.objects.create(
        organization=org,
        templates={"body": "Dear {name}: Hello!"},
        defaults={"name": "John", "Date": "08/31/2020"},
        type="test-org-welcome-message"
    )
    assert mt.pk is not None
    assert mt.organization == org
    assert mt.templates["body"] == "Dear {name}: Hello!"
    assert mt.defaults["name"] == "John"
    assert mt.type == "test-org-welcome-message"


def test_message_template_str():
    org = Organization.objects.create(display_name="Test Org", slug="test-org")
    mt = MessageTemplate.objects.create(
        organization=org,
        templates={},
        defaults={},
        type="test-type"
    )
    assert str(mt) == f"{org} test-type"


def test_unique_constraint():
    org = Organization.objects.create(display_name="Test Org", slug="test-org")
    MessageTemplate.objects.create(
        organization=org,
        templates={},
        defaults={},
        type="unique-type"
    )
    with pytest.raises(Exception):
        MessageTemplate.objects.create(
            organization=org,
            templates={},
            defaults={},
            type="unique-type"
        )
