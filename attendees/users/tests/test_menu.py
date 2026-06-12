import pytest
from django.contrib.auth.models import Group
from attendees.whereabouts.models import Organization
from attendees.users.models import Menu, MenuAuthGroup, User

@pytest.mark.django_db
class TestMenu:
    def setup_method(self):
        self.organization = Organization.objects.create(
            display_name="Test Organization",
            slug="test-org"
        )
        self.group = Group.objects.create(name="Test Group")
        self.menu = Menu.objects.create(
            organization=self.organization,
            category="main",
            html_type="a",
            urn="/app/test/",
            url_name="test_view",
            display_name="Test Menu",
            display_order=1,
            infos={"class": "nav-link"}
        )
        self.user = User.objects.create(username="testuser")
        self.user.groups.add(self.group)

    def test_create_menu(self):
        assert self.menu.pk is not None
        assert self.menu.organization == self.organization
        assert self.menu.category == "main"
        assert self.menu.urn == "/app/test/"
        assert self.menu.url_name == "test_view"
        assert self.menu.display_name == "Test Menu"

    def test_str(self):
        expected_str = f"test-org MAIN Test Menu URN: .../app/test/"
        assert str(self.menu) == expected_str

    def test_organization_slug(self):
        assert self.menu.organization_slug == "test-org"

    def test_user_can_create_attendee(self):
        # By default, user doesn't have permission
        assert not Menu.user_can_create_attendee(self.user, url_name="test_view")

        # Create MenuAuthGroup to grant write access
        MenuAuthGroup.objects.create(
            auth_group=self.group,
            menu=self.menu,
            read=True,
            write=True
        )

        # Now user has write access via the group
        assert Menu.user_can_create_attendee(self.user, url_name="test_view")
