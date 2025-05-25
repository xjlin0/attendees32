import pytest
from django.core.exceptions import ValidationError
from attendees.users.models.user import User
from attendees.whereabouts.models import Organization

pytestmark = pytest.mark.django_db


def test_create_user():
    org = Organization.objects.create(display_name="Test Org", slug="test-org")
    user = User.objects.create_user(username="testuser", email="test@example.com", password="pass1234", organization=org)
    assert user.pk is not None
    assert user.organization == org
    assert user.email == "test@example.com"
    assert user.check_password("pass1234")


def test_unique_email_validation():
    org = Organization.objects.create(display_name="Test Org2", slug="test-org2")
    User.objects.create_user(username="user1", email="unique@example.com", password="pass1234", organization=org)
    with pytest.raises(ValidationError):
        User(username="user2", email="unique@example.com", organization=org).save()


def test_get_absolute_url():
    user = User.objects.create_user(username="urluser", email="url@example.com", password="pass1234")
    url = user.get_absolute_url()
    assert "/users/detail/urluser" in url or "/users/urluser" in url


def test_organization_pk():
    org = Organization.objects.create(display_name="Test Org3", slug="test-org3")
    user = User.objects.create_user(username="orguser", email="org@example.com", password="pass1234", organization=org)
    assert user.organization_pk() == org.pk
    user_no_org = User.objects.create_user(username="noorg", email="noorg@example.com", password="pass1234")
    assert user_no_org.organization_pk() is None

def test_userhistory_created_on_user_create():
    org = Organization.objects.create(display_name="Test Org", slug="test-org")
    user = User.objects.create_user(username="historyuser", email="history@example.com", password="pass1234", organization=org)
    # There should be at least one UserHistory record for this user
    history = user.history
    assert history.count() >= 1
    assert history.latest("pgh_created_at").username == "historyuser"

def test_userhistory_created_on_user_update():
    org2 = Organization.objects.create(display_name="Test Org2", slug="test-org2")
    user = User.objects.create_user(name="original_name", username="historyuser2", email="history2@example.com", password="pass1234", organization=org2)
    user.name = "new_name"
    user.save()
    # There should be at least two UserHistory records for this user
    history = user.history
    assert history.count() >= 2
    assert history.last().name == "new_name"
    assert history.first().name == "original_name"
